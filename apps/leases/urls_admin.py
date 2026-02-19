from django.urls import path

from . import views

app_name = "leases_admin"

urlpatterns = [
    path("leases/", views.lease_list, name="lease_list"),
]
