"""
AI Gateway admin URL routes.
"""

from django.urls import path

from . import views

app_name = "ai_admin"

urlpatterns = [
    # Dashboard
    path("", views.admin_dashboard, name="dashboard"),
    # Provider management
    path("providers/add/", views.admin_provider_create, name="provider_create"),
    path(
        "providers/add/<str:provider>/",
        views.admin_provider_create,
        name="provider_create_type",
    ),
    path("providers/<uuid:pk>/edit/", views.admin_provider_edit, name="provider_edit"),
    path(
        "providers/<uuid:pk>/delete/",
        views.admin_provider_delete,
        name="provider_delete",
    ),
    path("providers/<uuid:pk>/test/", views.admin_provider_test, name="provider_test"),
]
