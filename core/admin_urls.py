from django.urls import path
from . import admin_views

urlpatterns = [
    # Auth
    path('login/', admin_views.admin_login_view, name='admin_login'),
    path('logout/', admin_views.admin_logout_view, name='admin_logout'),

    # Dashboard Overview
    path('', admin_views.dashboard_view, name='admin_dashboard'),

    # Members Management
    path('members/', admin_views.members_list_view, name='admin_members'),
    path('members/add/', admin_views.member_add_view, name='admin_member_add'),
    path('members/<int:user_id>/', admin_views.member_detail_view, name='admin_member_detail'),
    path('members/<int:user_id>/edit/', admin_views.member_edit_view, name='admin_member_edit'),
    path('members/<int:user_id>/toggle/', admin_views.member_toggle_status_view, name='admin_member_toggle'),
    path('members/<int:user_id>/delete/', admin_views.member_delete_view, name='admin_member_delete'),

    # Membership Plans
    path('plans/', admin_views.plans_list_view, name='admin_plans'),
    path('plans/add/', admin_views.plan_add_view, name='admin_plan_add'),
    path('plans/<int:plan_id>/edit/', admin_views.plan_edit_view, name='admin_plan_edit'),
    path('plans/<int:plan_id>/delete/', admin_views.plan_delete_view, name='admin_plan_delete'),

    # Subscriptions
    path('subscriptions/', admin_views.subscriptions_list_view, name='admin_subscriptions'),
    path('subscriptions/assign/', admin_views.subscription_assign_view, name='admin_subscription_assign'),
    path('subscriptions/<int:sub_id>/renew/', admin_views.subscription_renew_view, name='admin_subscription_renew'),
    path('subscriptions/<int:sub_id>/cancel/', admin_views.subscription_cancel_view, name='admin_subscription_cancel'),

    # Billing & Payments
    path('payments/', admin_views.payments_list_view, name='admin_payments'),
    path('payments/add/', admin_views.payment_add_view, name='admin_payment_add'),
    path('payments/<int:payment_id>/', admin_views.payment_detail_view, name='admin_payment_detail'),
    path('payments/<int:payment_id>/status/', admin_views.payment_update_status_view, name='admin_payment_update_status'),
    path('payments/<int:payment_id>/invoice/', admin_views.payment_invoice_pdf_view, name='admin_payment_invoice_pdf'),

    # Attendance
    path('attendance/', admin_views.attendance_list_view, name='admin_attendance'),
    path('attendance/<int:att_id>/delete/', admin_views.attendance_delete_view, name='admin_attendance_delete'),

    # Reports & Analytics
    path('reports/', admin_views.reports_view, name='admin_reports'),
    path('reports/export/members/', admin_views.export_members_csv, name='admin_export_members'),
    path('reports/export/payments/', admin_views.export_payments_csv, name='admin_export_payments'),
    path('reports/export/attendance/', admin_views.export_attendance_csv, name='admin_export_attendance'),

    # Settings
    path('settings/', admin_views.settings_view, name='admin_settings'),
]
