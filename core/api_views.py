from rest_framework import viewsets, generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.utils import timezone
from django.conf import settings
from .models import DietPlan, MembershipPlan, Subscription, Trainer, ContactInquiry, MemberProfile
from .serializers import (
    DietPlanSerializer, MembershipPlanSerializer, SubscriptionSerializer,
    TrainerSerializer, ContactInquirySerializer, UserSerializer
)


class DietPlanViewSet(viewsets.ModelViewSet):
    """
    REST API for Diet Plans.
    Allows listing, creating, retrieving, updating and filtering diet plans by category.
    """
    queryset = DietPlan.objects.all()
    serializer_class = DietPlanSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category__iexact=category)
        return qs


class MembershipPlanViewSet(viewsets.ModelViewSet):
    """
    REST API for Gym Membership Plans.
    """
    queryset = MembershipPlan.objects.filter(is_active=True)
    serializer_class = MembershipPlanSerializer
    permission_classes = [permissions.AllowAny]


class SubscriptionViewSet(viewsets.ModelViewSet):
    """
    REST API for Gym Subscriptions.
    """
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        user_id = self.request.query_params.get('user_id')
        status_filter = self.request.query_params.get('status')
        if user_id:
            qs = qs.filter(user_id=user_id)
        elif self.request.user.is_authenticated and not (self.request.user.is_staff or self.request.user.is_superuser):
            qs = qs.filter(user=self.request.user)
        if status_filter:
            qs = qs.filter(status__iexact=status_filter)
        return qs

    def perform_create(self, serializer):
        """Save locally and push to SubTrack via its receive endpoint.
        The gym site sends a JSON payload with a unique external_subscription_id.
        If the request fails we log it but do not abort the local save.
        """
        user = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(user=user)

        # Build payload for SubTrack
        payload = {
            "external_subscription_id": f"gym-{instance.id}",
            "customer_name": instance.customer_name,
            "customer_email": instance.customer_email,
            "customer_phone": instance.phone,
            "plan_name": instance.plan_name,
            "billing_cycle": instance.billing_cycle,
            "amount": str(instance.price),
            "start_date": instance.start_date.isoformat() if instance.start_date else None,
            "expiry_date": instance.end_date.isoformat() if instance.end_date else None,
            "payment_status": instance.payment_status,
            "payment_method": instance.payment_method,
            "subscription_status": instance.status,
        }
        endpoint = getattr(settings, "SUBTRACK_ENDPOINT", None)
        api_key = getattr(settings, "SUBTRACK_API_KEY", None)
        if endpoint and api_key:
            try:
                headers = {"X-SubTrack-API-Key": api_key, "Content-Type": "application/json"}
                import json, requests
                resp = requests.post(endpoint, data=json.dumps(payload), headers=headers, timeout=8)
                resp.raise_for_status()
            except Exception as exc:
                print(f"[Gym → SubTrack] sync error: {exc}")
        else:
            print("[Gym → SubTrack] endpoint or API key not configured; skipping sync.")


class TrainerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    REST API for Gym Trainers.
    """
    queryset = Trainer.objects.filter(is_active=True)
    serializer_class = TrainerSerializer
    permission_classes = [permissions.AllowAny]


class ContactInquiryViewSet(viewsets.ModelViewSet):
    """
    REST API for Gym Contact Inquiries.
    """
    queryset = ContactInquiry.objects.all()
    serializer_class = ContactInquirySerializer
    permission_classes = [permissions.AllowAny]


class GymStatsAPIView(APIView):
    """
    REST API endpoint providing aggregated metrics:
    Total plans, Total spending/revenue, Active subscriptions, Expired subscriptions.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if request.user.is_authenticated and not (request.user.is_staff or request.user.is_superuser):
            qs = Subscription.objects.filter(user=request.user)
        else:
            qs = Subscription.objects.all()

        total_plans = qs.count()
        active_count = qs.filter(status='Active').count()
        expiring_soon_count = qs.filter(status='Expiring Soon').count()
        expired_count = qs.filter(status='Expired').count()
        total_revenue = sum(float(sub.price) for sub in qs)

        return Response({
            'total_plans': total_plans,
            'active_subscriptions': active_count,
            'expiring_soon': expiring_soon_count,
            'expired_subscriptions': expired_count,
            'total_revenue_inr': total_revenue,
            'server_time': timezone.now().isoformat(),
        })


class RegisterAPIView(APIView):
    """
    REST API endpoint for member registration.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        full_name = request.data.get('name', '')
        phone = request.data.get('phone', '')

        if not username or not email or not password:
            return Response({'error': 'username, email, and password are required'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already taken'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email already registered'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=full_name.split(' ')[0] if full_name else '',
            last_name=' '.join(full_name.split(' ')[1:]) if ' ' in full_name else ''
        )
        MemberProfile.objects.create(user=user, phone=phone)

        return Response({
            'message': 'User registered successfully',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
