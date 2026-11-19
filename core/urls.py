from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import api_views

# REST API Router
router = DefaultRouter()
router.register(r'plans', api_views.MembershipPlanViewSet, basename='api-plan')
router.register(r'diet-plans', api_views.DietPlanViewSet, basename='api-diet-plan')
router.register(r'subscriptions', api_views.SubscriptionViewSet, basename='api-subscription')
router.register(r'trainers', api_views.TrainerViewSet, basename='api-trainer')
router.register(r'inquiries', api_views.ContactInquiryViewSet, basename='api-inquiry')

urlpatterns = [
    # Frontend Pages
    path('', views.home, name='home'),
    path('diet-plans/', views.diet_plans_view, name='diet_plans'),
    path('diet-plans/<int:pk>/json/', views.diet_plan_detail_json, name='diet_plan_json'),
    path('diet-plans/<int:pk>/select/', views.select_diet_plan, name='select_diet_plan'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('checkout/<int:plan_id>/', views.checkout_view, name='checkout'),
    
    # REST API endpoints
    path('api/', include(router.urls)),
    path('api/stats/', api_views.GymStatsAPIView.as_view(), name='api-stats'),
    path('api/auth/register/', api_views.RegisterAPIView.as_view(), name='api-register'),
]

# Shortcut for legacy callers (non‑/api/ prefix)
from django.urls import re_path
from .api_views import SubscriptionViewSet

urlpatterns += [
    re_path(r'^subscriptions/$', SubscriptionViewSet.as_view({
        'get': 'list',
        'post': 'create',
    }), name='legacy-subscriptions')
]

