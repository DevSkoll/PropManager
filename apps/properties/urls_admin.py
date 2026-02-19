from django.urls import path

from . import views

app_name = "properties_admin"

urlpatterns = [
    path("properties/", views.property_list, name="property_list"),
]
