from django.urls import path

from . import views

app_name = "leases_admin"

urlpatterns = [
    path("leases/", views.admin_lease_list, name="lease_list"),
    path("leases/create/", views.admin_lease_create, name="lease_create"),
    path("leases/<uuid:pk>/", views.admin_lease_detail, name="lease_detail"),
    path("leases/<uuid:pk>/edit/", views.admin_lease_edit, name="lease_edit"),
    path("leases/<uuid:pk>/terms/add/", views.admin_lease_add_term, name="lease_add_term"),
]
