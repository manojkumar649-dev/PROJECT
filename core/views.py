from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
from datetime import timedelta
import csv
import json

from .models import DietPlan, MembershipPlan, Subscription, Trainer, ContactInquiry, MemberProfile


# ==========================================
# HOME & PUBLIC PAGES
# ==========================================

def home(request):
    plans = MembershipPlan.objects.filter(is_active=True)
    diet_plans = DietPlan.objects.filter(is_featured=True)[:6]
    trainers = Trainer.objects.filter(is_active=True)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        message = request.POST.get('message', '').strip()
        if name and email and message:
            ContactInquiry.objects.create(name=name, email=email, message=message)
            messages.success(request, "Thank you! Your message has been received. Our team will contact you shortly.")
            return redirect('home')
        else:
            messages.error(request, "Please fill in all fields before sending.")

    context = {
        'plans': plans,
        'diet_plans': diet_plans,
        'trainers': trainers,
    }
    return render(request, 'gym_web.html', context)


def diet_plans_view(request):
    """Dedicated page to browse and view all Diet Plans from DB."""
    category = request.GET.get('category', 'all')
    if category and category != 'all':
        diet_plans = DietPlan.objects.filter(category=category)
    else:
        diet_plans = DietPlan.objects.all()

    categories = [c[0] for c in DietPlan.CATEGORY_CHOICES]
    
    context = {
        'diet_plans': diet_plans,
        'categories': categories,
        'selected_category': category,
    }
    return render(request, 'diet_plans.html', context)


def diet_plan_detail_json(request, pk):
    """AJAX endpoint for modal preview of a diet plan."""
    plan = get_object_or_404(DietPlan, pk=pk)
    data = {
        'id': plan.id,
        'title': plan.title,
        'category': plan.category,
        'target_calories': plan.target_calories,
        'protein': plan.protein_grams,
        'carbs': plan.carbs_grams,
        'fats': plan.fats_grams,
        'description': plan.description,
        'breakfast': plan.breakfast,
        'mid_morning': plan.mid_morning,
        'lunch': plan.lunch,
        'evening_snack': plan.evening_snack,
        'dinner': plan.dinner,
        'hydration': str(plan.hydration_water_liters),
        'key_tips': plan.key_tips,
        'image_url': plan.image_url,
    }
    return JsonResponse(data)


@login_required
def select_diet_plan(request, pk):
    plan = get_object_or_404(DietPlan, pk=pk)
    profile, _ = MemberProfile.objects.get_or_create(user=request.user)
    profile.current_diet_plan = plan
    profile.save()
    messages.success(request, f"Successfully activated '{plan.title}' as your active diet plan!")
    return redirect('diet_plans')


# ==========================================
# AUTHENTICATION
# ==========================================

def register_view(request):
    plans = MembershipPlan.objects.filter(is_active=True)
    
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        full_name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        age = request.POST.get('age', '').strip()
        gender = request.POST.get('gender', '').strip()
        plan_id = request.POST.get('plan', '').strip()
        fitness_goal = request.POST.get('goal', '').strip()
        password = request.POST.get('password', '').strip()

        # Validate
        if not full_name or not email or not password:
            messages.error(request, "Name, Email, and Password are required.")
            return render(request, 'gym_form.html', {'plans': plans})

        # Check existing email/username
        username = email.split('@')[0]
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists. Please log in.")
            return redirect('login')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=full_name.split(' ')[0],
            last_name=' '.join(full_name.split(' ')[1:]) if ' ' in full_name else ''
        )

        # Profile
        MemberProfile.objects.create(
            user=user,
            phone=phone,
            age=int(age) if age and age.isdigit() else None,
            gender=gender,
            fitness_goal=fitness_goal
        )

        # If a plan was selected during registration, create subscription
        if plan_id:
            try:
                selected_plan = MembershipPlan.objects.get(id=plan_id)
                Subscription.objects.create(
                    user=user,
                    customer_name=full_name,
                    customer_email=email,
                    phone=phone,
                    plan=selected_plan,
                    plan_name=selected_plan.name,
                    price=selected_plan.price,
                    billing_cycle=selected_plan.billing_cycle,
                    status='Active',
                    payment_method='UPI',
                    payment_status='Paid',
                    transaction_id=f"TXN-REG-{timezone.now().strftime('%Y%m%d%H%M%S')}"
                )
                messages.success(request, f"Welcome {full_name}! Your {selected_plan.name} membership has been activated!")
            except MembershipPlan.DoesNotExist:
                pass
        else:
            messages.success(request, f"Welcome to FitZone, {full_name}! Your account has been created.")

        login(request, user)
        return redirect('home')

    return render(request, 'gym_form.html', {'plans': plans})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        login_input = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        user = None
        # Try username or email
        if '@' in login_input:
            try:
                user_obj = User.objects.get(email=login_input)
                user = authenticate(request, username=user_obj.username, password=password)
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                user = None
        else:
            user = authenticate(request, username=login_input, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('home')
        else:
            messages.error(request, "Invalid email/username or password. Please try again.")

    return render(request, 'dash_logpage.html')


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('home')


# ==========================================
# MEMBERSHIP CHECKOUT / PAYMENT
# ==========================================

@login_required
def checkout_view(request, plan_id):
    plan = get_object_or_404(MembershipPlan, id=plan_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip() or request.user.get_full_name() or request.user.username
        email = request.POST.get('email', '').strip() or request.user.email
        payment_method = request.POST.get('payment_method', 'UPI')
        coupon = request.POST.get('coupon', '').strip().upper()
        
        final_price = plan.price
        if coupon == 'FIT10':
            final_price = round(plan.price * Decimal('0.90'), 2)
        elif coupon == 'FIT20':
            final_price = round(plan.price * Decimal('0.80'), 2)

        # Create the Subscription in SQLite!
        subscription = Subscription.objects.create(
            user=request.user,
            customer_name=name,
            customer_email=email,
            plan=plan,
            plan_name=plan.name,
            price=final_price,
            billing_cycle=plan.billing_cycle,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=plan.duration_days),
            status='Active',
            payment_method=payment_method,
            payment_status='Paid',
            transaction_id=f"TXN-{timezone.now().strftime('%Y%m%d%H%M%S')}-{request.user.id}",
            notes=f"Subscribed via Gym Site checkout. Coupon: {coupon if coupon else 'None'}"
        )

        messages.success(request, f"Payment successful! You are now subscribed to '{plan.name}'.")
        return redirect('home')

    context = {
        'plan': plan,
        'user': request.user,
    }
    return render(request, 'payment.html', context)

    context = {
        'plan': plan,
        'user': request.user,
    }
    return render(request, 'payment.html', context)



