from django.contrib import admin
from .models import DietPlan, MembershipPlan, Subscription, Trainer, ContactInquiry, MemberProfile, Attendance, Payment


@admin.register(DietPlan)
class DietPlanAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'target_calories', 'protein_grams', 'carbs_grams', 'fats_grams', 'is_featured')
    list_filter = ('category', 'is_featured')
    search_fields = ('title', 'description', 'breakfast', 'lunch', 'dinner')


@admin.register(MembershipPlan)
class MembershipPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'billing_cycle', 'duration_days', 'badge', 'is_popular', 'is_active')
    list_filter = ('billing_cycle', 'is_popular', 'is_active')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'plan_name', 'price', 'start_date', 'end_date', 'status', 'payment_method')
    list_filter = ('status', 'billing_cycle', 'payment_method', 'start_date')
    search_fields = ('customer_name', 'customer_email', 'plan_name', 'transaction_id')


@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'experience', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('name', 'bio')


@admin.register(ContactInquiry)
class ContactInquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at')
    search_fields = ('name', 'email', 'message')


@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'age', 'gender', 'current_diet_plan')
    search_fields = ('user__username', 'user__email', 'phone')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'check_in_time', 'check_out_time', 'status')
    list_filter = ('status', 'date')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'user', 'amount', 'payment_method', 'payment_status', 'payment_date')
    list_filter = ('payment_status', 'payment_method', 'payment_date')
    search_fields = ('invoice_number', 'user__username', 'user__email', 'transaction_id')
