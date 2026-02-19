from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.decorators import admin_required

from .forms import WeatherAlertForm, WeatherMonitorConfigForm
from .models import WeatherAlert, WeatherMonitorConfig, WeatherSnapshot


@admin_required
def weather_dashboard(request):
    configs = (
        WeatherMonitorConfig.objects
        .filter(is_active=True)
        .select_related("property")
    )

    # For each active config, attach the latest snapshot and active alert count
    property_weather = []
    for config in configs:
        latest_snapshot = (
            WeatherSnapshot.objects
            .filter(property=config.property)
            .first()
        )
        active_alert_count = (
            WeatherAlert.objects
            .filter(property=config.property)
            .count()
        )
        property_weather.append({
            "config": config,
            "snapshot": latest_snapshot,
            "alert_count": active_alert_count,
        })

    recent_alerts = (
        WeatherAlert.objects
        .select_related("property")
        .order_by("-created_at")[:10]
    )

    context = {
        "property_weather": property_weather,
        "recent_alerts": recent_alerts,
        "total_configs": configs.count(),
        "total_alerts": WeatherAlert.objects.count(),
    }
    return render(request, "weather/dashboard.html", context)


@admin_required
def weather_config_list(request):
    configs = (
        WeatherMonitorConfig.objects
        .select_related("property")
        .order_by("-created_at")
    )
    context = {"configs": configs}
    return render(request, "weather/config_list.html", context)


@admin_required
def weather_config_create(request):
    if request.method == "POST":
        form = WeatherMonitorConfigForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Weather monitoring configuration created successfully.")
            return redirect("weather_admin:weather_config_list")
    else:
        form = WeatherMonitorConfigForm()

    context = {"form": form, "is_edit": False}
    return render(request, "weather/config_form.html", context)


@admin_required
def weather_config_edit(request, pk):
    config = get_object_or_404(WeatherMonitorConfig, pk=pk)
    if request.method == "POST":
        form = WeatherMonitorConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Weather monitoring configuration updated successfully.")
            return redirect("weather_admin:weather_config_list")
    else:
        form = WeatherMonitorConfigForm(instance=config)

    context = {"form": form, "config": config, "is_edit": True}
    return render(request, "weather/config_form.html", context)


@admin_required
def weather_alert_list(request):
    alerts = (
        WeatherAlert.objects
        .select_related("property", "snapshot")
        .order_by("-created_at")
    )

    # Filters
    alert_type = request.GET.get("alert_type")
    severity = request.GET.get("severity")
    property_pk = request.GET.get("property")

    if alert_type:
        alerts = alerts.filter(alert_type=alert_type)
    if severity:
        alerts = alerts.filter(severity=severity)
    if property_pk:
        alerts = alerts.filter(property_id=property_pk)

    context = {
        "alerts": alerts,
        "alert_type_choices": WeatherAlert.ALERT_TYPE_CHOICES,
        "severity_choices": WeatherAlert.SEVERITY_CHOICES,
        "current_alert_type": alert_type or "",
        "current_severity": severity or "",
        "current_property": property_pk or "",
    }
    return render(request, "weather/alert_list.html", context)


@admin_required
def weather_alert_detail(request, pk):
    alert = get_object_or_404(
        WeatherAlert.objects.select_related("property", "snapshot"),
        pk=pk,
    )
    context = {"alert": alert}
    return render(request, "weather/alert_detail.html", context)


@admin_required
def weather_snapshot_list(request, property_pk):
    from apps.properties.models import Property

    property_obj = get_object_or_404(Property, pk=property_pk)
    snapshots = (
        WeatherSnapshot.objects
        .filter(property=property_obj)
        .order_by("-timestamp")
    )

    context = {
        "property": property_obj,
        "snapshots": snapshots,
    }
    return render(request, "weather/snapshot_list.html", context)
