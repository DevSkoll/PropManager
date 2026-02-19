from django.contrib import admin

from .models import WeatherAlert, WeatherMonitorConfig, WeatherSnapshot


@admin.register(WeatherMonitorConfig)
class WeatherMonitorConfigAdmin(admin.ModelAdmin):
    list_display = ("property", "is_active", "polling_interval_hours")
    list_filter = ("is_active",)


@admin.register(WeatherSnapshot)
class WeatherSnapshotAdmin(admin.ModelAdmin):
    list_display = ("property", "timestamp", "temperature_f", "wind_speed_mph", "alert_type")
    list_filter = ("alert_type",)


@admin.register(WeatherAlert)
class WeatherAlertAdmin(admin.ModelAdmin):
    list_display = ("title", "property", "alert_type", "severity", "notification_sent", "created_at")
    list_filter = ("alert_type", "severity", "notification_sent")
