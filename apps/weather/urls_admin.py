from django.urls import path

from . import views

app_name = "weather_admin"

urlpatterns = [
    path("weather/", views.weather_dashboard, name="weather_dashboard"),
    path("weather/config/", views.weather_config_list, name="weather_config_list"),
    path("weather/config/create/", views.weather_config_create, name="weather_config_create"),
    path("weather/config/<uuid:pk>/edit/", views.weather_config_edit, name="weather_config_edit"),
    path("weather/config/<uuid:pk>/detail/", views.weather_config_detail_modal, name="weather_config_detail_modal"),
    path("weather/config/<uuid:pk>/force-poll/", views.weather_force_poll, name="weather_force_poll"),
    path("weather/config/<uuid:pk>/force-notify/", views.weather_force_notify, name="weather_force_notify"),
    path("weather/geocode/<uuid:pk>/", views.geocode_property, name="geocode_property"),
    path("weather/alerts/", views.weather_alert_list, name="weather_alert_list"),
    path("weather/alerts/<uuid:pk>/", views.weather_alert_detail, name="weather_alert_detail"),
    path("weather/snapshots/<uuid:property_pk>/", views.weather_snapshot_list, name="weather_snapshot_list"),
    path("weather/rules/", views.notification_rule_list, name="notification_rule_list"),
    path("weather/rules/create/", views.notification_rule_create, name="notification_rule_create"),
    path("weather/rules/<uuid:pk>/edit/", views.notification_rule_edit, name="notification_rule_edit"),
    path("weather/rules/<uuid:pk>/delete/", views.notification_rule_delete, name="notification_rule_delete"),
    path("weather/rules/<uuid:pk>/log/", views.notification_rule_dispatch_log, name="notification_rule_dispatch_log"),
]
