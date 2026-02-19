from django.urls import path

from . import views

app_name = "notifications_tenant"

urlpatterns = [
    path("notification-preferences/", views.tenant_notification_preferences, name="preferences"),
]
