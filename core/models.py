from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class DietPlan(models.Model):
    CATEGORY_CHOICES = [
        ('Weight Loss', 'Weight Loss / Fat Burn'),
        ('Muscle Gain', 'Muscle Gain / Hypertrophy'),
        ('Keto Diet', 'Keto / Low Carb'),
        ('High Protein', 'High Protein Athletic'),
        ('Maintenance', 'General Health & Maintenance'),
        ('Vegetarian', 'Vegetarian Fitness Diet'),
    ]

    title = models.CharField(max_length=150)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='High Protein')
    target_calories = models.IntegerField(help_text="Daily calories target (kcal)")
    protein_grams = models.IntegerField(help_text="Protein in grams")
    carbs_grams = models.IntegerField(help_text="Carbs in grams")
    fats_grams = models.IntegerField(help_text="Fats in grams")
    description = models.TextField()
    
    # Meal Schedule Breakdown
    breakfast = models.TextField(help_text="Breakfast recommendations")
    mid_morning = models.TextField(blank=True, help_text="Mid-morning snack")
    lunch = models.TextField(help_text="Lunch recommendations")
    evening_snack = models.TextField(blank=True, help_text="Pre/Post workout or evening snack")
    dinner = models.TextField(help_text="Dinner recommendations")
    
    hydration_water_liters = models.DecimalField(max_digits=4, decimal_places=1, default=3.5)
    key_tips = models.TextField(blank=True, help_text="Important guidelines or supplement tips")
    image_url = models.URLField(max_length=500, blank=True, default='')
    is_featured = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.category} - {self.target_calories} kcal)"


class MembershipPlan(models.Model):
    CYCLE_CHOICES = [
        ('Monthly', 'Monthly (30 Days)'),
        ('Quarterly', 'Quarterly (90 Days)'),
        ('Half-Yearly', 'Half-Yearly (180 Days)'),
        ('Yearly', 'Yearly (365 Days)'),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_cycle = models.CharField(max_length=30, choices=CYCLE_CHOICES, default='Monthly')
    duration_days = models.IntegerField(default=30)
    description = models.TextField(blank=True)
    features = models.TextField(help_text="Features separated by newlines")
    badge = models.CharField(max_length=50, blank=True, help_text="e.g. POPULAR, BEST VALUE, VIP")
    is_popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['price']

    def __str__(self):
        return f"{self.name} - ₹{self.price} ({self.billing_cycle})"

    def feature_list(self):
        return [f.strip() for f in self.features.split('\n') if f.strip()]

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Subscription(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Expiring Soon', 'Expiring Soon'),
        ('Expired', 'Expired'),
        ('Cancelled', 'Cancelled'),
    ]
    PAYMENT_CHOICES = [
        ('UPI', 'UPI / GPay / PhonePe'),
        ('Credit Card', 'Credit Card'),
        ('Debit Card', 'Debit Card'),
        ('Net Banking', 'Net Banking'),
        ('Cash', 'Cash'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions', null=True, blank=True)
    customer_name = models.CharField(max_length=150)
    customer_email = models.EmailField()
    phone = models.CharField(max_length=25, blank=True)
    plan = models.ForeignKey(MembershipPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions')
    plan_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_cycle = models.CharField(max_length=30, default='Monthly')
    start_date = models.DateField(default=timezone.localdate)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Active')
    payment_method = models.CharField(max_length=30, choices=PAYMENT_CHOICES, default='UPI')
    payment_status = models.CharField(max_length=30, default='Paid')
    transaction_id = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer_name} - {self.plan_name} ({self.status})"

    def _normalize_date(self, val):
        if val is None:
            return None
        if hasattr(val, 'date') and callable(val.date):
            return val.date()
        return val

    def update_status(self):
        today = timezone.localdate()
        end = self._normalize_date(self.end_date)
        if end:
            if end < today:
                self.status = 'Expired'
            elif (end - today).days <= 7:
                self.status = 'Expiring Soon'
            else:
                self.status = 'Active'

    @property
    def days_remaining(self):
        end = self._normalize_date(self.end_date)
        if not end:
            return 0
        today = timezone.localdate()
        diff = (end - today).days
        return max(0, diff)

    def save(self, *args, **kwargs):
        self.start_date = self._normalize_date(self.start_date) or timezone.localdate()
        if not self.end_date:
            days = 30
            if self.plan:
                days = self.plan.duration_days
                if not self.plan_name:
                    self.plan_name = self.plan.name
                if not self.price:
                    self.price = self.plan.price
                if not self.billing_cycle:
                    self.billing_cycle = self.plan.billing_cycle
            self.end_date = self.start_date + timedelta(days=days)
        else:
            self.end_date = self._normalize_date(self.end_date)
        
        # Determine status dynamically unless explicitly Cancelled
        if self.status != 'Cancelled':
            self.update_status()

        super().save(*args, **kwargs)


class Trainer(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    experience = models.CharField(max_length=50, default='5+ Years')
    bio = models.TextField(blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.role}"


class ContactInquiry(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Inquiry from {self.name} ({self.email})"


class MemberProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=25, blank=True)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    fitness_goal = models.TextField(blank=True)
    current_diet_plan = models.ForeignKey(DietPlan, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Late', 'Late'),
        ('Half Day', 'Half Day'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(default=timezone.localdate)
    check_in_time = models.TimeField(default=timezone.now)
    check_out_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Present')
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-check_in_time']

    def __str__(self):
        return f"{self.user.username} - {self.date} ({self.status})"


class Payment(models.Model):
    STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Pending', 'Pending'),
        ('Failed', 'Failed'),
        ('Refunded', 'Refunded'),
    ]

    METHOD_CHOICES = [
        ('UPI', 'UPI / GPay / PhonePe'),
        ('Credit Card', 'Credit Card'),
        ('Debit Card', 'Debit Card'),
        ('Net Banking', 'Net Banking'),
        ('Cash', 'Cash'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=30, choices=METHOD_CHOICES, default='UPI')
    payment_status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Paid')
    payment_date = models.DateTimeField(default=timezone.now)
    transaction_id = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"{self.invoice_number} - ₹{self.amount} ({self.payment_status})"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            import uuid
            self.invoice_number = f"INV-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)


# Signal Handlers for automatic synchronization
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Subscription)
def sync_subscription_payment(sender, instance, created, **kwargs):
    if instance.price is not None:
        payment = Payment.objects.filter(subscription=instance).first()
        status_val = 'Paid' if instance.payment_status == 'Paid' else ('Pending' if instance.payment_status == 'Pending' else 'Paid')
        if not payment:
            date_val = instance.created_at if instance.created_at else timezone.now()
            Payment.objects.create(
                invoice_number=f"INV-{date_val.strftime('%Y%m%d')}-{instance.id:04d}",
                user=instance.user,
                subscription=instance,
                amount=instance.price,
                payment_method=instance.payment_method if instance.payment_method else 'UPI',
                payment_status=status_val,
                payment_date=date_val,
                transaction_id=instance.transaction_id or f"TXN-SUB-{instance.id}",
                notes=f"Payment for {instance.plan_name} ({instance.billing_cycle})"
            )
        else:
            payment.amount = instance.price
            payment.payment_status = status_val
            if instance.payment_method:
                payment.payment_method = instance.payment_method
            if instance.user:
                payment.user = instance.user
            payment.save()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        MemberProfile.objects.get_or_create(user=instance)

