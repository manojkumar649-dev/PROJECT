import csv
import io
from decimal import Decimal
from datetime import datetime, timedelta, date, time
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from .models import (
    DietPlan,
    MembershipPlan,
    Subscription,
    Trainer,
    ContactInquiry,
    MemberProfile,
    Attendance,
    Payment
)


# ==========================================
# AUTHENTICATION & ACCESS CONTROL
# ==========================================

def admin_required(view_func):
    """
    Decorator for views that checks that the user is logged in and is a staff
    or superuser. If not authenticated, redirects to admin login.
    If authenticated but not staff, shows error and redirects to home.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please log in with admin/staff credentials.")
            return redirect(f"/admin-dashboard/login/?next={request.path}")
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, "Access restricted. You do not have administrator permissions.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_login_view(request):
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('admin_dashboard')

    if request.method == 'POST':
        login_input = request.POST.get('username_or_email', '').strip()
        password = request.POST.get('password', '').strip()

        user = None
        if '@' in login_input:
            try:
                user_obj = User.objects.get(email__iexact=login_input)
                user = authenticate(request, username=user_obj.username, password=password)
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                user = None
        else:
            user = authenticate(request, username=login_input, password=password)

        if user is not None:
            if user.is_staff or user.is_superuser:
                login(request, user)
                messages.success(request, f"Welcome back, Administrator {user.first_name or user.username}!")
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('admin_dashboard')
            else:
                messages.error(request, "Access Denied: Your account does not have staff or administrator privileges.")
        else:
            messages.error(request, "Invalid administrator credentials. Please check your username/password.")

    return render(request, 'admin_dashboard/login.html')


def admin_logout_view(request):
    logout(request)
    messages.info(request, "Administrator logged out successfully.")
    return redirect('admin_login')


# ==========================================
# DASHBOARD OVERVIEW
# ==========================================

@admin_required
def dashboard_view(request):
    # Recalculate expired subscriptions on the fly
    for sub in Subscription.objects.exclude(status='Cancelled'):
        old_status = sub.status
        sub.update_status()
        if sub.status != old_status:
            sub.save()

    now = timezone.now()
    today = timezone.localdate()

    # 1. Total Members (all non-superuser users)
    total_members = User.objects.filter(is_superuser=False).count()

    # 2. Active Memberships
    active_memberships = Subscription.objects.filter(status='Active').count()

    # 3. Expired Memberships
    expired_memberships = Subscription.objects.filter(status='Expired').count()

    # 4. Total Revenue (from actual paid payments)
    total_rev_agg = Payment.objects.filter(payment_status='Paid').aggregate(Sum('amount'))
    total_revenue = total_rev_agg['amount__sum'] or Decimal('0.00')

    # 5. Monthly Revenue
    monthly_rev_agg = Payment.objects.filter(
        payment_status='Paid',
        payment_date__year=today.year,
        payment_date__month=today.month
    ).aggregate(Sum('amount'))
    monthly_revenue = monthly_rev_agg['amount__sum'] or Decimal('0.00')

    # 6. Pending Payments
    pending_payments_count = Payment.objects.filter(payment_status='Pending').count()
    pending_payments_amt = Payment.objects.filter(payment_status='Pending').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    # 7. New Registrations (Current Month)
    new_registrations = User.objects.filter(
        is_superuser=False,
        date_joined__year=today.year,
        date_joined__month=today.month
    ).count()

    # Recent Data
    recent_members = User.objects.filter(is_superuser=False).select_related('profile').order_by('-date_joined')[:6]
    recent_subscriptions = Subscription.objects.all().order_by('-created_at')[:6]
    recent_payments = Payment.objects.all().select_related('user', 'subscription').order_by('-payment_date')[:6]

    # Attendance today
    today_attendance_count = Attendance.objects.filter(date=today).count()
    today_present = Attendance.objects.filter(date=today, status='Present').count()
    today_late = Attendance.objects.filter(date=today, status='Late').count()

    # Popular plans distribution
    plans_distribution = MembershipPlan.objects.annotate(
        subs_count=Count('subscriptions')
    ).order_by('-subs_count')

    context = {
        'total_members': total_members,
        'active_memberships': active_memberships,
        'expired_memberships': expired_memberships,
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        'pending_payments_count': pending_payments_count,
        'pending_payments_amt': pending_payments_amt,
        'new_registrations': new_registrations,
        'recent_members': recent_members,
        'recent_subscriptions': recent_subscriptions,
        'recent_payments': recent_payments,
        'today_attendance_count': today_attendance_count,
        'today_present': today_present,
        'today_late': today_late,
        'plans_distribution': plans_distribution,
    }
    return render(request, 'admin_dashboard/dashboard.html', context)


# ==========================================
# MEMBER MANAGEMENT
# ==========================================

@admin_required
def members_list_view(request):
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')

    members_qs = User.objects.filter(is_superuser=False).select_related('profile').order_by('-date_joined')

    if search_query:
        members_qs = members_qs.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(profile__phone__icontains=search_query)
        )

    # Attach latest subscription info to each member
    members_data = []
    for user in members_qs:
        profile, _ = MemberProfile.objects.get_or_create(user=user)
        latest_sub = Subscription.objects.filter(user=user).order_by('-created_at').first()
        sub_status = latest_sub.status if latest_sub else 'No Membership'
        expiry_date = latest_sub.end_date if latest_sub else None

        # Filter by status if requested
        if status_filter == 'active' and sub_status != 'Active':
            continue
        elif status_filter == 'expired' and sub_status != 'Expired':
            continue
        elif status_filter == 'inactive' and user.is_active:
            continue

        members_data.append({
            'user': user,
            'profile': profile,
            'latest_sub': latest_sub,
            'sub_status': sub_status,
            'expiry_date': expiry_date,
        })

    paginator = Paginator(members_data, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'members': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_count': len(members_data),
    }
    return render(request, 'admin_dashboard/members_list.html', context)


@admin_required
def member_detail_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile, _ = MemberProfile.objects.get_or_create(user=user)
    subscriptions = Subscription.objects.filter(user=user).order_by('-created_at')
    payments = Payment.objects.filter(user=user).order_by('-payment_date')
    attendances = Attendance.objects.filter(user=user).order_by('-date')[:30]
    available_plans = MembershipPlan.objects.filter(is_active=True)

    active_sub = subscriptions.filter(status='Active').first()

    context = {
        'member': user,
        'profile': profile,
        'subscriptions': subscriptions,
        'payments': payments,
        'attendances': attendances,
        'active_sub': active_sub,
        'available_plans': available_plans,
    }
    return render(request, 'admin_dashboard/member_detail.html', context)


@admin_required
def member_add_view(request):
    plans = MembershipPlan.objects.filter(is_active=True)
    diet_plans = DietPlan.objects.all()

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        age = request.POST.get('age', '').strip()
        gender = request.POST.get('gender', '').strip()
        fitness_goal = request.POST.get('fitness_goal', '').strip()
        plan_id = request.POST.get('plan_id', '').strip()
        diet_plan_id = request.POST.get('diet_plan_id', '').strip()

        if not email or not password:
            messages.error(request, "Email and Password are required.")
            return render(request, 'admin_dashboard/member_form.html', {'plans': plans, 'diet_plans': diet_plans})

        if not username:
            username = email.split('@')[0]

        # Prevent duplicate username/email
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        if User.objects.filter(email=email).exists():
            messages.error(request, "A member with this email already exists.")
            return render(request, 'admin_dashboard/member_form.html', {'plans': plans, 'diet_plans': diet_plans})

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=True
        )

        diet_plan = DietPlan.objects.filter(id=diet_plan_id).first() if diet_plan_id else None

        MemberProfile.objects.update_or_create(
            user=user,
            defaults={
                'phone': phone,
                'age': int(age) if age and age.isdigit() else None,
                'gender': gender,
                'fitness_goal': fitness_goal,
                'current_diet_plan': diet_plan
            }
        )

        # Optional initial subscription assignment
        if plan_id:
            try:
                plan = MembershipPlan.objects.get(id=plan_id)
                Subscription.objects.create(
                    user=user,
                    customer_name=f"{first_name} {last_name}".strip() or username,
                    customer_email=email,
                    phone=phone,
                    plan=plan,
                    plan_name=plan.name,
                    price=plan.price,
                    billing_cycle=plan.billing_cycle,
                    status='Active',
                    payment_method='Cash',
                    payment_status='Paid',
                    transaction_id=f"TXN-ADM-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    notes="Assigned by administrator on account creation."
                )
            except MembershipPlan.DoesNotExist:
                pass

        messages.success(request, f"Member '{user.get_full_name() or user.username}' registered successfully!")
        return redirect('admin_member_detail', user_id=user.id)

    return render(request, 'admin_dashboard/member_form.html', {'plans': plans, 'diet_plans': diet_plans, 'is_edit': False})


@admin_required
def member_edit_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile, _ = MemberProfile.objects.get_or_create(user=user)
    diet_plans = DietPlan.objects.all()

    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        user.is_active = request.POST.get('is_active') == 'on'

        # Check email uniqueness
        if email != user.email and User.objects.filter(email=email).exclude(id=user.id).exists():
            messages.error(request, "Another user already uses this email address.")
            return render(request, 'admin_dashboard/member_form.html', {'member': user, 'profile': profile, 'diet_plans': diet_plans, 'is_edit': True})

        user.email = email
        new_password = request.POST.get('new_password', '').strip()
        if new_password:
            user.set_password(new_password)
        user.save()

        # Update profile
        phone = request.POST.get('phone', '').strip()
        age = request.POST.get('age', '').strip()
        gender = request.POST.get('gender', '').strip()
        fitness_goal = request.POST.get('fitness_goal', '').strip()
        diet_plan_id = request.POST.get('diet_plan_id', '').strip()

        profile.phone = phone
        profile.age = int(age) if age and age.isdigit() else None
        profile.gender = gender
        profile.fitness_goal = fitness_goal
        profile.current_diet_plan = DietPlan.objects.filter(id=diet_plan_id).first() if diet_plan_id else None
        profile.save()

        messages.success(request, f"Member '{user.get_full_name() or user.username}' updated successfully.")
        return redirect('admin_member_detail', user_id=user.id)

    context = {
        'member': user,
        'profile': profile,
        'diet_plans': diet_plans,
        'is_edit': True
    }
    return render(request, 'admin_dashboard/member_form.html', context)


@admin_required
def member_toggle_status_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user.is_superuser:
        messages.error(request, "Cannot deactivate a superuser.")
        return redirect('admin_members')

    user.is_active = not user.is_active
    user.save()
    status_str = "activated" if user.is_active else "deactivated"
    messages.success(request, f"Member '{user.username}' has been {status_str}.")
    return redirect(request.META.get('HTTP_REFERER', 'admin_members'))


@admin_required
def member_delete_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user.is_superuser or user == request.user:
        messages.error(request, "Cannot delete superuser or your own administrator account.")
        return redirect('admin_members')

    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f"Member '{username}' and associated data deleted successfully.")
        return redirect('admin_members')

    return render(request, 'admin_dashboard/member_confirm_delete.html', {'member': user})


# ==========================================
# MEMBERSHIP PLANS MANAGEMENT
# ==========================================

@admin_required
def plans_list_view(request):
    plans = MembershipPlan.objects.annotate(active_subs=Count('subscriptions', filter=Q(subscriptions__status='Active'))).all()
    context = {'plans': plans}
    return render(request, 'admin_dashboard/plans_list.html', context)


@admin_required
def plan_add_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        price = request.POST.get('price', '').strip()
        billing_cycle = request.POST.get('billing_cycle', 'Monthly')
        duration_days = request.POST.get('duration_days', '30')
        badge = request.POST.get('badge', '').strip()
        description = request.POST.get('description', '').strip()
        features = request.POST.get('features', '').strip()
        is_popular = request.POST.get('is_popular') == 'on'
        is_active = request.POST.get('is_active') == 'on'

        if not name or not price:
            messages.error(request, "Plan name and price are required.")
            return render(request, 'admin_dashboard/plan_form.html', {'is_edit': False})

        plan = MembershipPlan.objects.create(
            name=name,
            price=Decimal(price),
            billing_cycle=billing_cycle,
            duration_days=int(duration_days) if duration_days.isdigit() else 30,
            badge=badge,
            description=description,
            features=features,
            is_popular=is_popular,
            is_active=is_active
        )
        messages.success(request, f"Membership plan '{plan.name}' created successfully!")
        return redirect('admin_plans')

    return render(request, 'admin_dashboard/plan_form.html', {'is_edit': False})


@admin_required
def plan_edit_view(request, plan_id):
    plan = get_object_or_404(MembershipPlan, id=plan_id)

    if request.method == 'POST':
        plan.name = request.POST.get('name', '').strip()
        price_val = request.POST.get('price', '').strip()
        plan.price = Decimal(price_val) if price_val else plan.price
        plan.billing_cycle = request.POST.get('billing_cycle', plan.billing_cycle)
        dur_val = request.POST.get('duration_days', '').strip()
        plan.duration_days = int(dur_val) if dur_val.isdigit() else plan.duration_days
        plan.badge = request.POST.get('badge', '').strip()
        plan.description = request.POST.get('description', '').strip()
        plan.features = request.POST.get('features', '').strip()
        plan.is_popular = request.POST.get('is_popular') == 'on'
        plan.is_active = request.POST.get('is_active') == 'on'
        plan.save()

        messages.success(request, f"Membership plan '{plan.name}' updated successfully.")
        return redirect('admin_plans')

    context = {'plan': plan, 'is_edit': True}
    return render(request, 'admin_dashboard/plan_form.html', context)


@admin_required
def plan_delete_view(request, plan_id):
    plan = get_object_or_404(MembershipPlan, id=plan_id)
    subs_count = Subscription.objects.filter(plan=plan).count()

    if request.method == 'POST':
        plan_name = plan.name
        if subs_count > 0:
            # Safely deactivate instead of deleting to preserve foreign key constraints
            plan.is_active = False
            plan.save()
            messages.warning(request, f"Plan '{plan_name}' has existing subscriptions. It has been deactivated instead of deleted.")
        else:
            plan.delete()
            messages.success(request, f"Plan '{plan_name}' deleted successfully.")
        return redirect('admin_plans')

    context = {'plan': plan, 'subs_count': subs_count}
    return render(request, 'admin_dashboard/plan_confirm_delete.html', context)


# ==========================================
# SUBSCRIPTION MANAGEMENT
# ==========================================

@admin_required
def subscriptions_list_view(request):
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('q', '').strip()

    subs = Subscription.objects.all().select_related('user', 'plan')

    # Update statuses dynamically
    for s in subs:
        s.update_status()

    if status_filter and status_filter != 'all':
        subs = subs.filter(status=status_filter)

    if search_query:
        subs = subs.filter(
            Q(customer_name__icontains=search_query) |
            Q(customer_email__icontains=search_query) |
            Q(plan_name__icontains=search_query) |
            Q(transaction_id__icontains=search_query)
        )

    paginator = Paginator(subs.order_by('-created_at'), 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'subscriptions': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'total_count': subs.count(),
    }
    return render(request, 'admin_dashboard/subscriptions_list.html', context)


@admin_required
def subscription_assign_view(request):
    members = User.objects.filter(is_superuser=False).order_by('first_name', 'username')
    plans = MembershipPlan.objects.filter(is_active=True)

    preselected_user_id = request.GET.get('user_id')

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        plan_id = request.POST.get('plan_id')
        payment_method = request.POST.get('payment_method', 'UPI')
        payment_status = request.POST.get('payment_status', 'Paid')
        start_date_str = request.POST.get('start_date', '')

        if not user_id or not plan_id:
            messages.error(request, "Please select both a member and a membership plan.")
            return render(request, 'admin_dashboard/subscription_form.html', {'members': members, 'plans': plans, 'preselected_user_id': preselected_user_id})

        user = get_object_or_404(User, id=user_id)
        plan = get_object_or_404(MembershipPlan, id=plan_id)
        profile, _ = MemberProfile.objects.get_or_create(user=user)

        start_date = timezone.localdate()
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        end_date = start_date + timedelta(days=plan.duration_days)

        sub = Subscription.objects.create(
            user=user,
            customer_name=user.get_full_name() or user.username,
            customer_email=user.email,
            phone=profile.phone,
            plan=plan,
            plan_name=plan.name,
            price=plan.price,
            billing_cycle=plan.billing_cycle,
            start_date=start_date,
            end_date=end_date,
            status='Active',
            payment_method=payment_method,
            payment_status=payment_status,
            transaction_id=f"TXN-ADM-{timezone.now().strftime('%Y%m%d%H%M%S')}-{user.id}",
            notes=f"Assigned by Admin ({request.user.username})"
        )

        messages.success(request, f"Membership '{plan.name}' assigned to {user.get_full_name() or user.username}!")
        return redirect('admin_subscriptions')

    context = {
        'members': members,
        'plans': plans,
        'preselected_user_id': preselected_user_id,
        'today': timezone.localdate().strftime('%Y-%m-%d')
    }
    return render(request, 'admin_dashboard/subscription_form.html', context)


@admin_required
def subscription_renew_view(request, sub_id):
    sub = get_object_or_404(Subscription, id=sub_id)

    if request.method == 'POST':
        duration_days = sub.plan.duration_days if sub.plan else 30
        today = timezone.localdate()

        # If still active, extend from current end date; otherwise extend from today
        base_date = sub.end_date if (sub.end_date and sub.end_date > today) else today
        new_end_date = base_date + timedelta(days=duration_days)

        sub.start_date = today if sub.end_date and sub.end_date <= today else sub.start_date
        sub.end_date = new_end_date
        sub.status = 'Active'
        sub.payment_status = 'Paid'
        sub.save()

        # Record renewal payment
        Payment.objects.create(
            invoice_number=f"INV-REN-{timezone.now().strftime('%Y%m%d')}-{sub.id:04d}",
            user=sub.user,
            subscription=sub,
            amount=sub.price,
            payment_method=sub.payment_method or 'UPI',
            payment_status='Paid',
            payment_date=timezone.now(),
            transaction_id=f"TXN-REN-{timezone.now().strftime('%Y%m%d%H%M%S')}",
            notes=f"Renewal payment for {sub.plan_name} until {new_end_date}"
        )

        messages.success(request, f"Membership for '{sub.customer_name}' renewed successfully until {new_end_date}!")
        return redirect(request.META.get('HTTP_REFERER', 'admin_subscriptions'))

    context = {'subscription': sub}
    return render(request, 'admin_dashboard/subscription_renew_confirm.html', context)


@admin_required
def subscription_cancel_view(request, sub_id):
    sub = get_object_or_404(Subscription, id=sub_id)
    sub.status = 'Cancelled'
    sub.save()
    messages.warning(request, f"Subscription #{sub.id} for '{sub.customer_name}' has been marked as Cancelled.")
    return redirect(request.META.get('HTTP_REFERER', 'admin_subscriptions'))


# ==========================================
# BILLING AND PAYMENT MANAGEMENT
# ==========================================

@admin_required
def payments_list_view(request):
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')
    method_filter = request.GET.get('method', 'all')

    payments = Payment.objects.all().select_related('user', 'subscription')

    if status_filter and status_filter != 'all':
        payments = payments.filter(payment_status=status_filter)

    if method_filter and method_filter != 'all':
        payments = payments.filter(payment_method=method_filter)

    if search_query:
        payments = payments.filter(
            Q(invoice_number__icontains=search_query) |
            Q(transaction_id__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )

    # Statistics
    total_collected = Payment.objects.filter(payment_status='Paid').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    pending_amount = Payment.objects.filter(payment_status='Pending').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    failed_count = Payment.objects.filter(payment_status='Failed').count()

    paginator = Paginator(payments.order_by('-payment_date'), 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'payments': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'method_filter': method_filter,
        'total_collected': total_collected,
        'pending_amount': pending_amount,
        'failed_count': failed_count,
        'total_count': payments.count(),
    }
    return render(request, 'admin_dashboard/payments_list.html', context)


@admin_required
def payment_add_view(request):
    members = User.objects.filter(is_superuser=False).order_by('first_name', 'username')
    subs = Subscription.objects.all()

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        amount_str = request.POST.get('amount', '').strip()
        payment_method = request.POST.get('payment_method', 'UPI')
        payment_status = request.POST.get('payment_status', 'Paid')
        notes = request.POST.get('notes', '').strip()
        transaction_id = request.POST.get('transaction_id', '').strip()

        if not amount_str:
            messages.error(request, "Amount is required.")
            return render(request, 'admin_dashboard/payment_form.html', {'members': members})

        user = User.objects.filter(id=user_id).first() if user_id else None

        payment = Payment.objects.create(
            user=user,
            amount=Decimal(amount_str),
            payment_method=payment_method,
            payment_status=payment_status,
            transaction_id=transaction_id or f"TXN-MAN-{timezone.now().strftime('%Y%m%d%H%M%S')}",
            notes=notes or "Manually recorded payment."
        )

        messages.success(request, f"Payment #{payment.invoice_number} of ₹{payment.amount} recorded successfully!")
        return redirect('admin_payments')

    return render(request, 'admin_dashboard/payment_form.html', {'members': members})


@admin_required
def payment_detail_view(request, payment_id):
    payment = get_object_or_404(Payment.objects.select_related('user', 'subscription'), id=payment_id)
    return render(request, 'admin_dashboard/payment_detail.html', {'payment': payment})


@admin_required
def payment_update_status_view(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    new_status = request.POST.get('status')
    if new_status in ['Paid', 'Pending', 'Failed', 'Refunded']:
        payment.payment_status = new_status
        payment.save()
        if payment.subscription and new_status in ['Paid', 'Pending']:
            payment.subscription.payment_status = new_status
            payment.subscription.save()
        messages.success(request, f"Payment #{payment.invoice_number} marked as {new_status}.")
    return redirect(request.META.get('HTTP_REFERER', 'admin_payments'))


# ==========================================
# PDF INVOICE GENERATOR (REPORTLAB)
# ==========================================

@admin_required
def payment_invoice_pdf_view(request, payment_id):
    payment = get_object_or_404(Payment.objects.select_related('user', 'subscription'), id=payment_id)
    user = payment.user
    subscription = payment.subscription

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#dc2626')
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#64748b')
    )

    heading2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0f172a')
    )

    normal_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=14,
        textColor=colors.HexColor('#334155')
    )

    bold_style = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=14,
        textColor=colors.HexColor('#0f172a')
    )

    elements = []

    # Header with Gym Brand & Invoice Meta
    header_data = [
        [
            Paragraph("<b>FITZONE GYM & FITNESS CLUB</b><br/><font size=8 color='#64748b'>123 Elite Fitness Boulevard, Health District<br/>Contact: +91 98888 88888 | info@fitzone.com<br/>GSTIN: 33AAAAA0000A1Z5</font>", normal_style),
            Paragraph(f"<b><font size=16 color='#dc2626'>TAX INVOICE</font></b><br/><b>Invoice #:</b> {payment.invoice_number}<br/><b>Date:</b> {payment.payment_date.strftime('%d %b %Y')}<br/><b>Status:</b> <font color='{'#16a34a' if payment.payment_status == 'Paid' else '#eab308'}'><b>{payment.payment_status.upper()}</b></font>", normal_style)
        ]
    ]

    header_table = Table(header_data, colWidths=[3.8 * inch, 3.2 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 15))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=15))

    # Billed To & Payment Details
    customer_name = user.get_full_name() if user else (subscription.customer_name if subscription else "Walk-in Guest")
    customer_email = user.email if user else (subscription.customer_email if subscription else "N/A")
    customer_phone = (user.profile.phone if user and hasattr(user, 'profile') else (subscription.phone if subscription else "N/A")) or "N/A"

    info_data = [
        [
            Paragraph("<b>BILLED TO:</b>", bold_style),
            Paragraph("<b>PAYMENT INFORMATION:</b>", bold_style)
        ],
        [
            Paragraph(f"<b>{customer_name}</b><br/>Email: {customer_email}<br/>Phone: {customer_phone}<br/>Member ID: #{user.id if user else 'GUEST'}", normal_style),
            Paragraph(f"<b>Method:</b> {payment.payment_method}<br/><b>Transaction ID:</b> {payment.transaction_id or 'TXN-DIRECT'}<br/><b>Payment Date:</b> {payment.payment_date.strftime('%d %B %Y, %I:%M %p')}", normal_style)
        ]
    ]
    info_table = Table(info_data, colWidths=[3.8 * inch, 3.2 * inch])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))

    # Items Table
    item_title = subscription.plan_name if subscription else "Gym Membership & Facility Access"
    item_desc = f"Subscription Cycle: {subscription.billing_cycle if subscription else 'Direct'} | Duration: {subscription.plan.duration_days if (subscription and subscription.plan) else '30'} Days"

    items_data = [
        [
            Paragraph("<b>#</b>", bold_style),
            Paragraph("<b>ITEM & DESCRIPTION</b>", bold_style),
            Paragraph("<b>QTY</b>", bold_style),
            Paragraph("<b>RATE</b>", bold_style),
            Paragraph("<b>TOTAL</b>", bold_style)
        ],
        [
            Paragraph("1", normal_style),
            Paragraph(f"<b>{item_title}</b><br/><font size=7 color='#64748b'>{item_desc}</font>", normal_style),
            Paragraph("1", normal_style),
            Paragraph(f"₹{payment.amount}", normal_style),
            Paragraph(f"₹{payment.amount}", bold_style)
        ],
    ]

    items_table = Table(items_data, colWidths=[0.4 * inch, 3.8 * inch, 0.7 * inch, 1.1 * inch, 1.0 * inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor('#cbd5e1')),
        ('LINEBELOW', (0, 1), (-1, 1), 1, colors.HexColor('#e2e8f0')),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 15))

    # Totals breakdown
    totals_data = [
        [Paragraph("", normal_style), Paragraph("<b>Subtotal:</b>", normal_style), Paragraph(f"₹{payment.amount}", normal_style)],
        [Paragraph("", normal_style), Paragraph("<b>Taxes (CGST + SGST):</b>", normal_style), Paragraph("₹0.00", normal_style)],
        [Paragraph("", normal_style), Paragraph("<b>Grand Total:</b>", bold_style), Paragraph(f"<b><font size=12 color='#dc2626'>₹{payment.amount}</font></b>", bold_style)],
    ]
    totals_table = Table(totals_data, colWidths=[4.2 * inch, 1.6 * inch, 1.2 * inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEABOVE', (1, 2), (-1, 2), 1, colors.HexColor('#cbd5e1')),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 30))

    # Notes & Signature
    footer_data = [
        [
            Paragraph("<b>Terms & Conditions:</b><br/><font size=7 color='#64748b'>1. Membership fees are non-refundable.<br/>2. Members must adhere to gym code of conduct.<br/>3. Please bring towel and gym footwear at all times.</font>", normal_style),
            Paragraph("<br/><br/>___________________________<br/><b>Authorized Signatory</b><br/><font size=8 color='#64748b'>FitZone Management</font>", ParagraphStyle('Sign', parent=normal_style, alignment=TA_RIGHT))
        ]
    ]
    footer_table = Table(footer_data, colWidths=[4.5 * inch, 2.5 * inch])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(footer_table)

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Invoice_{payment.invoice_number}.pdf"'
    return response


# ==========================================
# ATTENDANCE MANAGEMENT
# ==========================================

@admin_required
def attendance_list_view(request):
    today = timezone.localdate()
    selected_date_str = request.GET.get('date', today.strftime('%Y-%m-%d'))
    search_query = request.GET.get('q', '').strip()

    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = today

    members = User.objects.filter(is_superuser=False).order_by('first_name', 'username')

    # Handle quick check-in POST
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        att_status = request.POST.get('status', 'Present')
        notes = request.POST.get('notes', '').strip()
        check_in_time_str = request.POST.get('check_in_time')

        if user_id:
            user = get_object_or_404(User, id=user_id)
            c_time = timezone.now().time()
            if check_in_time_str:
                try:
                    c_time = datetime.strptime(check_in_time_str, '%H:%M').time()
                except ValueError:
                    pass

            att, created = Attendance.objects.get_or_create(
                user=user,
                date=selected_date,
                defaults={
                    'check_in_time': c_time,
                    'status': att_status,
                    'notes': notes or 'Check-in via Admin Dashboard'
                }
            )
            if not created:
                att.status = att_status
                att.check_in_time = c_time
                if notes:
                    att.notes = notes
                att.save()
                messages.info(request, f"Attendance updated for {user.get_full_name() or user.username}.")
            else:
                messages.success(request, f"Attendance marked for {user.get_full_name() or user.username} as {att_status}!")
        return redirect(f"{request.path}?date={selected_date.strftime('%Y-%m-%d')}")

    attendance_qs = Attendance.objects.filter(date=selected_date).select_related('user', 'user__profile')

    if search_query:
        attendance_qs = attendance_qs.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    # Daily Stats
    total_attended = Attendance.objects.filter(date=selected_date).count()
    present_count = Attendance.objects.filter(date=selected_date, status='Present').count()
    late_count = Attendance.objects.filter(date=selected_date, status='Late').count()
    half_day_count = Attendance.objects.filter(date=selected_date, status='Half Day').count()

    context = {
        'attendance_list': attendance_qs.order_by('-check_in_time'),
        'members': members,
        'selected_date': selected_date.strftime('%Y-%m-%d'),
        'search_query': search_query,
        'total_attended': total_attended,
        'present_count': present_count,
        'late_count': late_count,
        'half_day_count': half_day_count,
        'current_time_str': timezone.localtime(timezone.now()).strftime('%H:%M'),
    }
    return render(request, 'admin_dashboard/attendance_list.html', context)


@admin_required
def attendance_delete_view(request, att_id):
    att = get_object_or_404(Attendance, id=att_id)
    att_date = att.date.strftime('%Y-%m-%d')
    att.delete()
    messages.success(request, "Attendance record removed.")
    return redirect(f"/admin-dashboard/attendance/?date={att_date}")


# ==========================================
# REPORTS & ANALYTICS
# ==========================================

@admin_required
def reports_view(request):
    today = timezone.localdate()

    # 1. Monthly Revenue for the last 6 months
    months_labels = []
    revenue_data = []
    members_growth_data = []

    for i in range(5, -1, -1):
        target_month_date = today - timedelta(days=i * 30)
        y = target_month_date.year
        m = target_month_date.month
        label = target_month_date.strftime('%b %Y')
        months_labels.append(label)

        # Revenue
        rev = Payment.objects.filter(
            payment_status='Paid',
            payment_date__year=y,
            payment_date__month=m
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        revenue_data.append(float(rev))

        # Member growth (cumulative or new joined in month)
        new_users = User.objects.filter(
            is_superuser=False,
            date_joined__year=y,
            date_joined__month=m
        ).count()
        members_growth_data.append(new_users)

    # 2. Membership status distribution
    active_count = Subscription.objects.filter(status='Active').count()
    expiring_count = Subscription.objects.filter(status='Expiring Soon').count()
    expired_count = Subscription.objects.filter(status='Expired').count()
    cancelled_count = Subscription.objects.filter(status='Cancelled').count()

    # 3. Popular plans
    plans_labels = []
    plans_counts = []
    for p in MembershipPlan.objects.all():
        plans_labels.append(p.name)
        plans_counts.append(p.subscriptions.count())

    # 4. Summary metrics
    total_revenue = Payment.objects.filter(payment_status='Paid').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_members = User.objects.filter(is_superuser=False).count()
    total_subscriptions = Subscription.objects.count()
    total_attendance = Attendance.objects.count()

    context = {
        'months_labels_json': months_labels,
        'revenue_data_json': revenue_data,
        'members_growth_json': members_growth_data,
        'status_labels': ['Active', 'Expiring Soon', 'Expired', 'Cancelled'],
        'status_data': [active_count, expiring_count, expired_count, cancelled_count],
        'plans_labels_json': plans_labels,
        'plans_counts_json': plans_counts,
        'total_revenue': total_revenue,
        'total_members': total_members,
        'total_subscriptions': total_subscriptions,
        'total_attendance': total_attendance,
    }
    return render(request, 'admin_dashboard/reports.html', context)


@admin_required
def export_members_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="members_export_{timezone.localdate()}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Member ID', 'Username', 'Full Name', 'Email', 'Phone', 'Age', 'Gender', 'Joined Date', 'Status', 'Active Plan'])

    for user in User.objects.filter(is_superuser=False).select_related('profile'):
        profile = getattr(user, 'profile', None)
        latest_sub = Subscription.objects.filter(user=user).order_by('-created_at').first()
        writer.writerow([
            user.id,
            user.username,
            user.get_full_name(),
            user.email,
            profile.phone if profile else '',
            profile.age if profile else '',
            profile.gender if profile else '',
            user.date_joined.strftime('%Y-%m-%d'),
            'Active' if user.is_active else 'Inactive',
            latest_sub.plan_name if latest_sub else 'None'
        ])
    return response


@admin_required
def export_payments_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="payments_export_{timezone.localdate()}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Invoice #', 'Date', 'Member Name', 'Email', 'Amount (INR)', 'Payment Method', 'Payment Status', 'Transaction ID', 'Notes'])

    for p in Payment.objects.all().select_related('user', 'subscription'):
        writer.writerow([
            p.invoice_number,
            p.payment_date.strftime('%Y-%m-%d %H:%M'),
            p.user.get_full_name() if p.user else (p.subscription.customer_name if p.subscription else 'Guest'),
            p.user.email if p.user else (p.subscription.customer_email if p.subscription else ''),
            p.amount,
            p.payment_method,
            p.payment_status,
            p.transaction_id,
            p.notes
        ])
    return response


@admin_required
def export_attendance_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendance_export_{timezone.localdate()}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Member ID', 'Member Name', 'Email', 'Check In Time', 'Status', 'Notes'])

    for att in Attendance.objects.all().select_related('user'):
        writer.writerow([
            att.date.strftime('%Y-%m-%d'),
            att.user.id,
            att.user.get_full_name() or att.user.username,
            att.user.email,
            att.check_in_time.strftime('%H:%M:%S'),
            att.status,
            att.notes
        ])
    return response


# ==========================================
# SETTINGS
# ==========================================

@admin_required
def settings_view(request):
    total_users = User.objects.count()
    total_plans = MembershipPlan.objects.count()
    total_subs = Subscription.objects.count()
    total_payments = Payment.objects.count()

    context = {
        'admin_user': request.user,
        'total_users': total_users,
        'total_plans': total_plans,
        'total_subs': total_subs,
        'total_payments': total_payments,
        'server_time': timezone.now(),
    }
    return render(request, 'admin_dashboard/settings.html', context)
