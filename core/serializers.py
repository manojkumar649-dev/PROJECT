from rest_framework import serializers
from django.contrib.auth.models import User
from .models import DietPlan, MembershipPlan, Subscription, Trainer, ContactInquiry, MemberProfile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class MemberProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = MemberProfile
        fields = '__all__'


class DietPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = DietPlan
        fields = '__all__'


class MembershipPlanSerializer(serializers.ModelSerializer):
    feature_list = serializers.ReadOnlyField()

    class Meta:
        model = MembershipPlan
        fields = '__all__'


class SubscriptionSerializer(serializers.ModelSerializer):
    days_remaining = serializers.ReadOnlyField()
    plan_details = MembershipPlanSerializer(source='plan', read_only=True)

    class Meta:
        model = Subscription
        fields = '__all__'

    def create(self, validated_data):
        # Auto attach user from request if authenticated
        request = self.context.get('request')
        if request and request.user.is_authenticated and not validated_data.get('user'):
            validated_data['user'] = request.user
            if not validated_data.get('customer_name'):
                validated_data['customer_name'] = request.user.get_full_name() or request.user.username
            if not validated_data.get('customer_email'):
                validated_data['customer_email'] = request.user.email
        return super().create(validated_data)


class TrainerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trainer
        fields = '__all__'


class ContactInquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInquiry
        fields = '__all__'
