from django.urls import path

from . import views
from apps.core import views_api

app_name = "accounts_admin"

urlpatterns = [
    path("login/", views.admin_login, name="admin_login"),
    path("login/verify/", views.admin_otp_verify, name="admin_otp_verify"),
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("analytics/", views.admin_analytics_dashboard, name="admin_analytics_dashboard"),
    path("tenants/", views.admin_tenant_list, name="admin_tenant_list"),
    path("tenants/<uuid:pk>/modal/", views.admin_tenant_detail_modal, name="admin_tenant_detail_modal"),
    path("tenants/<uuid:pk>/delete/", views.admin_tenant_delete, name="admin_tenant_delete"),
    path("tenants/<uuid:pk>/archive/", views.admin_tenant_archive, name="admin_tenant_archive"),
    path("tenants/<uuid:pk>/restore/", views.admin_tenant_restore, name="admin_tenant_restore"),
    path("settings/", views.admin_settings, name="admin_settings"),
    path("logout/", views.user_logout, name="admin_logout"),
    # API endpoints
    path("api/search/", views_api.global_search_api, name="admin_global_search"),
]
