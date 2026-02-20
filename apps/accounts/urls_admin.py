from django.urls import path

from . import views

app_name = "accounts_admin"

urlpatterns = [
    path("login/", views.admin_login, name="admin_login"),
    path("login/verify/", views.admin_otp_verify, name="admin_otp_verify"),
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("analytics/", views.admin_analytics_dashboard, name="admin_analytics_dashboard"),
    path("tenants/", views.admin_tenant_list, name="admin_tenant_list"),
    path("settings/", views.admin_settings, name="admin_settings"),
    path("logout/", views.user_logout, name="admin_logout"),
]
