from django.urls import path

from . import views

app_name = "communications_tenant"

urlpatterns = [
    path("messages/", views.tenant_thread_list, name="thread_list"),
    path("messages/create/", views.tenant_thread_create, name="thread_create"),
    path("messages/<uuid:pk>/", views.tenant_thread_detail, name="thread_detail"),
    path("notifications/", views.tenant_notification_list, name="notification_list"),
]
