from django.urls import path

from . import views

app_name = "properties_admin"

urlpatterns = [
    path("properties/", views.property_list, name="property_list"),
    path("properties/create/", views.property_create, name="property_create"),
    path("properties/<uuid:pk>/", views.property_detail, name="property_detail"),
    path("properties/<uuid:pk>/edit/", views.property_edit, name="property_edit"),
    path("properties/<uuid:property_pk>/units/create/", views.unit_create, name="unit_create"),
    path("properties/<uuid:property_pk>/units/<uuid:pk>/", views.unit_detail, name="unit_detail"),
    path("properties/<uuid:property_pk>/units/<uuid:pk>/edit/", views.unit_edit, name="unit_edit"),
]
