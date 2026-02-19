from django.urls import path

from . import views

app_name = "accounts_admin"

urlpatterns = [
    path("login/", views.admin_login, name="admin_login"),
    path("login/verify/", views.admin_otp_verify, name="admin_otp_verify"),
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("logout/", views.user_logout, name="admin_logout"),
]
