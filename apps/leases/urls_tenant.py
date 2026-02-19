from django.urls import path

from . import views

app_name = "leases_tenant"

urlpatterns = [
    path("leases/", views.tenant_lease_detail, name="lease_detail"),
]
