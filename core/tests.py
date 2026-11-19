from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from core.models import DietPlan, MembershipPlan, Subscription, Trainer, MemberProfile


class FitZoneGymTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'pass123', first_name='Test', last_name='User')
        self.profile = MemberProfile.objects.create(user=self.user, phone='1234567890')
        
        self.plan = MembershipPlan.objects.create(
            name='Test Gold Plan',
            slug='test-gold-plan',
            price=1500.00,
            billing_cycle='Monthly',
            duration_days=30,
            features='Gym Access\nSauna',
            is_active=True
        )

        self.diet = DietPlan.objects.create(
            title='Test High Protein',
            category='High Protein',
            target_calories=2500,
            protein_grams=160,
            carbs_grams=220,
            fats_grams=60,
            description='Test description',
            breakfast='Eggs and oats',
            lunch='Chicken and rice',
            dinner='Fish and veggies',
            is_featured=True
        )

    def test_home_page_loads(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'FITZONE')
        self.assertContains(response, 'Test Gold Plan')
        self.assertContains(response, 'Test High Protein')

    def test_diet_plans_page_and_filtering(self):
        response = self.client.get(reverse('diet_plans'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test High Protein')

        # Test filter
        filtered_response = self.client.get(reverse('diet_plans') + '?category=High+Protein')
        self.assertEqual(filtered_response.status_code, 200)
        self.assertContains(filtered_response, 'Test High Protein')

    def test_user_registration(self):
        reg_data = {
            'name': 'New Member',
            'email': 'newmember@example.com',
            'password': 'memberpass123',
            'phone': '9988776655',
            'age': '24',
            'gender': 'Male',
            'plan': self.plan.id,
            'goal': 'Lose weight'
        }
        response = self.client.post(reverse('register'), reg_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(email='newmember@example.com').exists())
        # Subscription should have been auto created!
        new_user = User.objects.get(email='newmember@example.com')
        self.assertTrue(Subscription.objects.filter(user=new_user).exists())

    def test_user_login(self):
        login_res = self.client.post(reverse('login'), {'email': 'test@example.com', 'password': 'pass123'}, follow=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertTrue(login_res.context['user'].is_authenticated)

    def test_add_membership_subscription(self):
        self.client.login(username='testuser', password='pass123')
        
        # Checkout membership
        checkout_res = self.client.post(reverse('checkout', args=[self.plan.id]), {
            'name': 'Test User',
            'email': 'test@example.com',
            'payment_method': 'UPI',
            'coupon': 'FIT10'
        }, follow=True)
        self.assertEqual(checkout_res.status_code, 200)

        # Check subscription exists in DB
        sub = Subscription.objects.filter(user=self.user, plan=self.plan).first()
        self.assertIsNotNone(sub)
        self.assertEqual(sub.status, 'Active')
        # 10% coupon discount applied: 1500 - 150 = 1350
        self.assertEqual(float(sub.price), 1350.00)

    def test_rest_api_endpoints(self):
        # Plans API
        api_plans = self.client.get('/api/plans/')
        self.assertEqual(api_plans.status_code, 200)

        # Diet Plans API
        api_diet = self.client.get('/api/diet-plans/')
        self.assertEqual(api_diet.status_code, 200)

        # Subscriptions API
        api_subs = self.client.get('/api/subscriptions/')
        self.assertEqual(api_subs.status_code, 200)

        # Stats API
        api_stats = self.client.get('/api/stats/')
        self.assertEqual(api_stats.status_code, 200)
        self.assertIn('total_plans', api_stats.json())
