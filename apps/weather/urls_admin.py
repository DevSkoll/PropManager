from django.urls import path

from . import views

app_name = "weather_admin"

urlpatterns = [
    path("weather/", views.weather_dashboard, name="weather_dashboard"),
    path("weather/config/", views.weather_config_list, name="weather_config_list"),
    path("weather/config/create/", views.weather_config_create, name="weather_config_create"),
    path("weather/config/<uuid:pk>/edit/", views.weather_config_edit, name="weather_config_edit"),
    path("weather/alerts/", views.weather_alert_list, name="weather_alert_list"),
    path("weather/alerts/<uuid:pk>/", views.weather_alert_detail, name="weather_alert_detail"),
    path("weather/snapshots/<uuid:property_pk>/", views.weather_snapshot_list, name="weather_snapshot_list"),
]
