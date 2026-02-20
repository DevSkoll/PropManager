from django.urls import path

from . import views

app_name = "leases_tenant"

urlpatterns = [
    path("leases/", views.tenant_lease_list, name="lease_list"),
    path("leases/current/", views.tenant_lease_detail, name="lease_detail"),
    path("leases/<uuid:pk>/", views.tenant_lease_detail, name="lease_detail_by_id"),
]
