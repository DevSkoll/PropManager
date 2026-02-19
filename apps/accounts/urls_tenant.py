from django.urls import path

from . import views

app_name = "accounts_tenant"

urlpatterns = [
    path("login/", views.tenant_login, name="tenant_login"),
    path("login/verify/", views.tenant_otp_verify, name="tenant_otp_verify"),
    path("dashboard/", views.tenant_dashboard, name="tenant_dashboard"),
    path("profile/", views.tenant_profile, name="tenant_profile"),
    path("logout/", views.user_logout, name="tenant_logout"),
]
