from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("tenant/", include("apps.accounts.urls_tenant")),
    path("admin-portal/", include("apps.accounts.urls_admin")),
    path("contractor/", include("apps.workorders.urls_contractor")),
    path("tenant/", include("apps.properties.urls_tenant")),
    path("admin-portal/", include("apps.properties.urls_admin")),
    path("tenant/", include("apps.leases.urls_tenant")),
    path("admin-portal/", include("apps.leases.urls_admin")),
    path("tenant/", include("apps.billing.urls_tenant")),
    path("admin-portal/", include("apps.billing.urls_admin")),
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
    path("", RedirectView.as_view(url="/tenant/login/", permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
