import os
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gym_project.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from core.models import DietPlan, MembershipPlan, Subscription, Trainer, MemberProfile, ContactInquiry


def seed():
    print("--- Starting Database Seeding ---")

    # 1. Superuser & Demo User
    if not User.objects.filter(username='admin').exists():
        admin_user = User.objects.create_superuser('admin', 'admin@fitzone.com', 'admin123')
        admin_user.first_name = "Admin"
        admin_user.last_name = "Manager"
        admin_user.save()
        MemberProfile.objects.get_or_create(user=admin_user, phone="+91 9888888888", age=30, gender="Male")
        print("Created Superuser: admin / admin123")
    else:
        admin_user = User.objects.get(username='admin')

    if not User.objects.filter(username='john').exists():
        john = User.objects.create_user('john', 'john@example.com', 'password123', first_name='John', last_name='Doe')
        MemberProfile.objects.get_or_create(user=john, phone="+91 9876543210", age=26, gender="Male", fitness_goal="Muscle gain & core strength")
        print("Created Demo User: john / password123")
    else:
        john = User.objects.get(username='john')

    # 2. Membership Plans
    plans_data = [
        {
            'name': 'Basic Plan',
            'slug': 'basic-plan',
            'price': 999.00,
            'billing_cycle': 'Monthly',
            'duration_days': 30,
            'description': 'Essential gym access for entry-level fitness enthusiasts.',
            'features': "Full Gym Equipment Access\nStandard Locker Room Access\nCardio Zone Access\nWater & Shower Facilities",
            'badge': 'STARTER',
            'is_popular': False,
        },
        {
            'name': 'Standard Plan',
            'slug': 'standard-plan',
            'price': 1999.00,
            'billing_cycle': 'Monthly',
            'duration_days': 30,
            'description': 'Our most popular comprehensive membership for serious gains.',
            'features': "Everything in Basic Plan\nPersonal Trainer Consultation\nCustom Diet Plan in DB\nWeekly Body Composition Scan\nFree Zumba & Yoga Classes",
            'badge': 'MOST POPULAR',
            'is_popular': True,
        },
        {
            'name': 'Elite VIP Plan',
            'slug': 'elite-vip-plan',
            'price': 2999.00,
            'billing_cycle': 'Monthly',
            'duration_days': 30,
            'description': 'All-inclusive premium experience with recovery spa & unlimited coaching.',
            'features': "Everything in Standard Plan\nDedicated Personal Coach\nSpa, Sauna & Steam Bath Access\nUnlimited Group & Crossfit Classes\nFree Protein Shake Daily\nSubTrack Priority Support",
            'badge': 'VIP ACCESS',
            'is_popular': False,
        },
        {
            'name': 'Annual Pro Pass',
            'slug': 'annual-pro-pass',
            'price': 9999.00,
            'billing_cycle': 'Yearly',
            'duration_days': 365,
            'description': 'Unbeatable full year fitness package with maximum savings.',
            'features': "365 Days Unlimited All-Gym Access\n24/7 Dedicated Fitness & Nutrition Coach\nQuarterly In-Depth Health Checks\nFitZone Apparel & Shaker Kit\n2 Guest Passes Monthly",
            'badge': 'BEST VALUE',
            'is_popular': False,
        },
    ]

    for p in plans_data:
        plan_obj, created = MembershipPlan.objects.get_or_create(slug=p['slug'], defaults=p)
        if created:
            print(f"Created Membership Plan: {plan_obj.name}")

    # 3. Diet Plans in DB
    diet_data = [
        {
            'title': 'High Protein Hypertrophy & Muscle Gain',
            'category': 'Muscle Gain',
            'target_calories': 2800,
            'protein_grams': 185,
            'carbs_grams': 250,
            'fats_grams': 65,
            'description': 'Engineered for rapid muscular hypertrophy, recovery, and strength gains with clean caloric surplus.',
            'breakfast': '4 whole eggs scrambled, 1 cup rolled oats with 1 scoop whey protein, sliced banana, and a handful of almonds.',
            'mid_morning': 'Greek yogurt (200g) with chia seeds, blueberries, and 1 scoop peanut butter toast.',
            'lunch': '220g grilled chicken breast or grilled paneer, 1.5 cups brown rice or quinoa, steamed broccoli and olive oil salad.',
            'evening_snack': 'Post-workout whey isolate shake, 2 rice cakes with honey, and 1 green apple.',
            'dinner': '200g grilled salmon or tofu, baked sweet potatoes, sauteed asparagus with garlic.',
            'hydration_water_liters': 4.0,
            'key_tips': 'Consume 5g creatine monohydrate daily. Ensure at least 8 hours of sleep for optimum protein synthesis and muscle recovery.',
            'image_url': 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=800&q=80',
            'is_featured': True
        },
        {
            'title': 'Caloric Deficit Rapid Fat Burn & Lean Tone',
            'category': 'Weight Loss',
            'target_calories': 1750,
            'protein_grams': 155,
            'carbs_grams': 115,
            'fats_grams': 45,
            'description': 'High satiety, thermogenic diet plan designed to incinerate stubborn body fat while preserving lean muscle mass.',
            'breakfast': '3 egg white omelette with spinach, mushrooms, tomatoes, and 1 slice 100% whole grain sourdough toast.',
            'mid_morning': '1 cup hot green tea, 1 small handful walnuts, and 1 sweet orange.',
            'lunch': '180g grilled lemon herb chicken breast / soy chunks, large garden salad with avocado oil, half cup steamed brown rice.',
            'evening_snack': '1 scoop whey protein with chilled unsweetened almond milk and cucumber celery sticks.',
            'dinner': '180g steamed white fish or grilled light paneer, cauliflower mash, and a bowl of green beans.',
            'hydration_water_liters': 3.8,
            'key_tips': 'Stop eating 3 hours before bed. Keep sodium moderate and take 10,000 steps daily in addition to gym lifting.',
            'image_url': 'https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=800&q=80',
            'is_featured': True
        },
        {
            'title': 'Ketogenic Metabolic Performance Shred',
            'category': 'Keto Diet',
            'target_calories': 2100,
            'protein_grams': 140,
            'carbs_grams': 25,
            'fats_grams': 160,
            'description': 'Ultra low carb, healthy fats ketogenic protocol for steady fat burning, sustained mental clarity, and zero insulin spikes.',
            'breakfast': '3 eggs fried in grass-fed butter, half avocado, 2 strips Turkey bacon, and black coffee with MCT oil.',
            'mid_morning': 'Macadamia nuts (30g) and pumpkin seeds with string cheese.',
            'lunch': 'Zucchini noodles tossed with pesto sauce, olive oil, and 200g grilled salmon or paneer.',
            'evening_snack': 'Celery sticks dipped in almond butter and electrolyte water.',
            'dinner': 'Grass-fed beef steak or grilled spiced paneer, creamed spinach with garlic and parmesan cheese.',
            'hydration_water_liters': 4.2,
            'key_tips': 'Replenish electrolytes (sodium, potassium, magnesium) daily to avoid keto fatigue and maintain explosive gym workouts.',
            'image_url': 'https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=800&q=80',
            'is_featured': True
        },
        {
            'title': 'Vegetarian Plant Power & Core Fitness',
            'category': 'Vegetarian',
            'target_calories': 2250,
            'protein_grams': 135,
            'carbs_grams': 260,
            'fats_grams': 55,
            'description': 'Complete plant-rich nutrition with diverse amino acids from lentils, paneer, tofu, nuts, and complex carbohydrates.',
            'breakfast': 'Sprouted moong dal cheela / pancakes with mint chutney, 1 glass soy milk, and 1 cup soaked almonds.',
            'mid_morning': 'Mixed fruit bowl (papaya, kiwi, apple) topped with flax seeds and hemp protein.',
            'lunch': 'Tofu or paneer tikka masala (low oil), yellow dal tadka, 2 multigrain rotis, and fresh cucumber salad.',
            'evening_snack': 'Roasted chickpeas (chana), black coffee, and roasted pumpkin seeds.',
            'dinner': 'Lentil vegetable soup, baked sweet potato wedges, sauteed bell peppers, and low-fat cottage cheese.',
            'hydration_water_liters': 3.5,
            'key_tips': 'Combine legumes with whole grains to ensure complete amino acid profiling for muscle maintenance.',
            'image_url': 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=800&q=80',
            'is_featured': True
        },
    ]

    for d in diet_data:
        dp, created = DietPlan.objects.get_or_create(title=d['title'], defaults=d)
        if created:
            print(f"Created Diet Plan in DB: {dp.title}")

    # Attach one diet plan to John's profile
    john_profile = MemberProfile.objects.get(user=john)
    if not john_profile.current_diet_plan:
        john_profile.current_diet_plan = DietPlan.objects.first()
        john_profile.save()

    # 4. Trainers
    trainers_data = [
        {
            'name': 'David Miller',
            'role': 'Strength & Conditioning Head Coach',
            'experience': '10+ Years',
            'bio': 'Former powerlifting champion specializing in compound lifts, hypertrophy, and periodized athletic training.',
            'image_url': 'https://images.unsplash.com/photo-1567013127542-490d757e51fc?auto=format&fit=crop&w=800&q=80',
        },
        {
            'name': 'Sophia Rodriguez',
            'role': 'Yoga & Functional Mobility Coach',
            'experience': '7+ Years',
            'bio': 'Certified Ashtanga yoga master and functional movement specialist helping athletes build balance and flexibility.',
            'image_url': 'https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=800&q=80',
        },
        {
            'name': 'James Wilson',
            'role': 'HIIT & Fat Loss Transformation Coach',
            'experience': '8+ Years',
            'bio': 'CrossFit certified coach with expertise in high-intensity metabolic conditioning and rapid fat loss routines.',
            'image_url': 'https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?auto=format&fit=crop&w=800&q=80',
        },
    ]

    for t in trainers_data:
        t_obj, created = Trainer.objects.get_or_create(name=t['name'], defaults=t)
        if created:
            print(f"Created Trainer: {t_obj.name}")

    # 5. Seed initial SubTrack Subscriptions for Demo
    today = timezone.now().date()
    standard_plan = MembershipPlan.objects.get(slug='standard-plan')
    elite_plan = MembershipPlan.objects.get(slug='elite-vip-plan')
    basic_plan = MembershipPlan.objects.get(slug='basic-plan')

    demo_subs = [
        {
            'user': john,
            'customer_name': 'John Doe',
            'customer_email': 'john@example.com',
            'phone': '+91 9876543210',
            'plan': standard_plan,
            'plan_name': standard_plan.name,
            'price': standard_plan.price,
            'billing_cycle': standard_plan.billing_cycle,
            'start_date': today - timedelta(days=10),
            'end_date': today + timedelta(days=20),
            'status': 'Active',
            'payment_method': 'UPI',
            'payment_status': 'Paid',
            'transaction_id': 'TXN-FIT-982103',
            'notes': 'Added via FitZone website'
        },
        {
            'user': admin_user,
            'customer_name': 'Sarah Connor',
            'customer_email': 'sarah.c@gymfit.com',
            'phone': '+91 9811223344',
            'plan': elite_plan,
            'plan_name': elite_plan.name,
            'price': elite_plan.price,
            'billing_cycle': elite_plan.billing_cycle,
            'start_date': today - timedelta(days=25),
            'end_date': today + timedelta(days=5),
            'status': 'Expiring Soon',
            'payment_method': 'Credit Card',
            'payment_status': 'Paid',
            'transaction_id': 'TXN-FIT-771239',
            'notes': 'VIP Member'
        },
        {
            'user': admin_user,
            'customer_name': 'Marcus Vance',
            'customer_email': 'marcus.v@fitness.org',
            'phone': '+91 9766554433',
            'plan': basic_plan,
            'plan_name': basic_plan.name,
            'price': basic_plan.price,
            'billing_cycle': basic_plan.billing_cycle,
            'start_date': today - timedelta(days=45),
            'end_date': today - timedelta(days=15),
            'status': 'Expired',
            'payment_method': 'Debit Card',
            'payment_status': 'Paid',
            'transaction_id': 'TXN-FIT-441209',
            'notes': 'Previous monthly member'
        },
    ]

    for s in demo_subs:
        sub_obj, created = Subscription.objects.get_or_create(
            transaction_id=s['transaction_id'],
            defaults=s
        )
        if created:
            print(f"Created Subscription: {sub_obj.customer_name} - {sub_obj.plan_name}")

    print("--- Database Seeding Completed Successfully! ---")


if __name__ == '__main__':
    seed()
