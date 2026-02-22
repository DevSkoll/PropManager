from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from apps.core.views import health_check, liveness_check, readiness_check

urlpatterns = [
    # Health check endpoints for container orchestration
    path("health/", health_check, name="health_check"),
    path("live/", liveness_check, name="liveness_check"),
    path("ready/", readiness_check, name="readiness_check"),
    # Django admin
    path("django-admin/", admin.site.urls),
    path("tenant/", include("apps.accounts.urls_tenant")),
    path("admin-portal/", include("apps.accounts.urls_admin")),
    path("contractor/", include("apps.workorders.urls_contractor")),
    path("tenant/", include("apps.properties.urls_tenant")),
    path("admin-portal/", include("apps.properties.urls_admin")),
    path("tenant/", include("apps.leases.urls_tenant")),
    path("admin-portal/", include("apps.leases.urls_admin")),
    path("lease/", include("apps.leases.urls_signing")),
    path("tenant/", include("apps.billing.urls_tenant")),
    path("admin-portal/", include("apps.billing.urls_admin")),
    path("tenant/", include("apps.rewards.urls_tenant")),
    path("admin-portal/", include("apps.rewards.urls_admin")),
    path("tenant/", include("apps.workorders.urls_tenant")),
    path("admin-portal/", include("apps.workorders.urls_admin")),
    path("tenant/", include("apps.communications.urls_tenant")),
    path("admin-portal/", include("apps.communications.urls_admin")),
    path("tenant/", include("apps.documents.urls_tenant")),
    path("admin-portal/", include("apps.documents.urls_admin")),
    path("admin-portal/", include("apps.weather.urls_admin")),
    path("admin-portal/", include("apps.marketing.urls_admin")),
    path("admin-portal/", include("apps.notifications.urls_admin")),
    path("tenant/", include("apps.notifications.urls_tenant")),
    path("admin-portal/", include("apps.core.reports.urls")),
    path("admin-portal/onboarding/", include(("apps.tenant_lifecycle.urls_admin", "tenant_lifecycle"), namespace="tenant_lifecycle_admin")),
    path("onboard/", include(("apps.tenant_lifecycle.urls_onboarding", "tenant_lifecycle"), namespace="tenant_lifecycle")),
    path("admin-portal/ai/", include("apps.ai.urls_admin")),
    # Setup wizard
    path("setup/", include("apps.setup.urls")),
    path("", RedirectView.as_view(url="/tenant/login/", permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Django Debug Toolbar
    try:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
