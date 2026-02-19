from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.decorators import admin_required

from .forms import WeatherAlertForm, WeatherMonitorConfigForm, WeatherNotificationRuleForm
from .models import (
    WeatherAlert,
    WeatherMonitorConfig,
    WeatherNotificationRule,
    WeatherRuleDispatchLog,
    WeatherSnapshot,
)


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
def weather_config_detail_modal(request, pk):
    """AJAX endpoint: return HTML fragment for the config detail modal."""
    from django.db.models import Q

    config = get_object_or_404(
        WeatherMonitorConfig.objects.select_related("property"),
        pk=pk,
    )
    prop = config.property

    applicable_rules = (
        WeatherNotificationRule.objects
        .filter(is_active=True)
        .filter(Q(property=prop) | Q(property__isnull=True))
        .order_by("alert_type", "name")
    )

    last_dispatch = (
        WeatherRuleDispatchLog.objects
        .filter(property=prop)
        .select_related("rule", "alert")
        .order_by("-dispatched_at")
        .first()
    )

    dispatch_history = (
        WeatherRuleDispatchLog.objects
        .filter(property=prop)
        .select_related("rule", "alert")
        .order_by("-dispatched_at")[:20]
    )

    recent_alerts = (
        WeatherAlert.objects
        .filter(property=prop)
        .select_related("snapshot")
        .order_by("-created_at")[:10]
    )

    latest_alert = (
        WeatherAlert.objects
        .filter(property=prop)
        .order_by("-created_at")
        .first()
    )

    context = {
        "config": config,
        "applicable_rules": applicable_rules,
        "last_dispatch": last_dispatch,
        "dispatch_history": dispatch_history,
        "recent_alerts": recent_alerts,
        "latest_alert": latest_alert,
    }
    return render(request, "weather/_config_detail_modal.html", context)


@admin_required
def weather_force_poll(request, pk):
    """Force an immediate weather poll for a config."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    config = get_object_or_404(
        WeatherMonitorConfig.objects.select_related("property"),
        pk=pk,
    )

    from django_q.tasks import async_task
    async_task(
        "apps.weather.tasks.poll_weather_for_property",
        str(config.id),
    )

    return JsonResponse({
        "success": True,
        "message": f"Weather poll queued for {config.property.name}.",
    })


@admin_required
def weather_force_notify(request, pk):
    """Force re-run notification rules for the latest alert on a config's property."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    config = get_object_or_404(
        WeatherMonitorConfig.objects.select_related("property"),
        pk=pk,
    )

    latest_alert = (
        WeatherAlert.objects
        .filter(property=config.property)
        .order_by("-created_at")
        .first()
    )
    if not latest_alert:
        return JsonResponse({
            "success": False,
            "message": "No alerts exist for this property.",
        }, status=404)

    from django_q.tasks import async_task
    async_task(
        "apps.weather.tasks.process_notification_rules",
        str(latest_alert.id),
    )

    return JsonResponse({
        "success": True,
        "message": f"Notification processing queued for alert: {latest_alert.title}.",
    })


@admin_required
def geocode_property(request, pk):
    """AJAX endpoint: return lat/lng for a property based on its ZIP code."""
    from apps.core.services.weather import weather_service
    from apps.properties.models import Property

    prop = get_object_or_404(Property, pk=pk)
    if not prop.zip_code:
        return JsonResponse({"error": "Property has no ZIP code"}, status=400)

    result = weather_service.geocode_zip(prop.zip_code)
    if result is None:
        return JsonResponse({"error": "Could not geocode ZIP code"}, status=502)

    return JsonResponse({
        "latitude": result["lat"],
        "longitude": result["lon"],
        "zip_code": prop.zip_code,
    })


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


@admin_required
def notification_rule_list(request):
    rules = (
        WeatherNotificationRule.objects
        .select_related("property")
        .order_by("-created_at")
    )
    context = {"rules": rules}
    return render(request, "weather/rule_list.html", context)


@admin_required
def notification_rule_create(request):
    if request.method == "POST":
        form = WeatherNotificationRuleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Notification rule created successfully.")
            return redirect("weather_admin:notification_rule_list")
    else:
        form = WeatherNotificationRuleForm()

    context = {"form": form, "is_edit": False}
    return render(request, "weather/rule_form.html", context)


@admin_required
def notification_rule_edit(request, pk):
    rule = get_object_or_404(WeatherNotificationRule, pk=pk)
    if request.method == "POST":
        form = WeatherNotificationRuleForm(request.POST, instance=rule)
        if form.is_valid():
            form.save()
            messages.success(request, "Notification rule updated successfully.")
            return redirect("weather_admin:notification_rule_list")
    else:
        form = WeatherNotificationRuleForm(instance=rule)

    context = {"form": form, "rule": rule, "is_edit": True}
    return render(request, "weather/rule_form.html", context)


@admin_required
def notification_rule_delete(request, pk):
    rule = get_object_or_404(WeatherNotificationRule, pk=pk)
    if request.method == "POST":
        rule.delete()
        messages.success(request, "Notification rule deleted.")
        return redirect("weather_admin:notification_rule_list")

    context = {"rule": rule}
    return render(request, "weather/rule_confirm_delete.html", context)


@admin_required
def notification_rule_dispatch_log(request, pk):
    rule = get_object_or_404(WeatherNotificationRule, pk=pk)
    logs = (
        WeatherRuleDispatchLog.objects
        .filter(rule=rule)
        .select_related("property", "alert")
        .order_by("-dispatched_at")
    )
    context = {"rule": rule, "logs": logs}
    return render(request, "weather/rule_dispatch_log.html", context)
