import logging
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

logger = logging.getLogger(__name__)


def poll_weather_for_all_properties():
    """Fetch weather for all active WeatherMonitorConfigs.

    Intended to be scheduled via Django-Q2. Iterates over every active
    configuration and dispatches an individual poll task for each one.
    """
    from django_q.tasks import async_task

    from .models import WeatherMonitorConfig

    configs = WeatherMonitorConfig.objects.filter(is_active=True)
    count = 0
    for config in configs:
        async_task(
            "apps.weather.tasks.poll_weather_for_property",
            str(config.id),
        )
        count += 1

    logger.info("Dispatched weather polling for %d properties", count)
    return count


def poll_weather_for_property(config_id):
    """Fetch weather for a single property, store a snapshot, and check thresholds.

    Args:
        config_id: UUID (as string) of the WeatherMonitorConfig.
    """
    from django_q.tasks import async_task

    from apps.core.services.weather import weather_service

    from .models import WeatherMonitorConfig, WeatherSnapshot

    try:
        config = WeatherMonitorConfig.objects.select_related("property").get(
            id=config_id, is_active=True
        )
    except WeatherMonitorConfig.DoesNotExist:
        logger.warning("WeatherMonitorConfig %s not found or inactive", config_id)
        return None

    data = weather_service.get_current_weather(config.latitude, config.longitude)
    if data is None:
        logger.error("No weather data returned for config %s", config_id)
        return None

    # Parse the OpenWeatherMap response
    temperature_f = Decimal(str(data["main"]["temp"]))
    feels_like_f = Decimal(str(data["main"]["feels_like"]))
    humidity = data["main"]["humidity"]
    wind_speed_mph = Decimal(str(data["wind"]["speed"]))
    wind_gust_mph = Decimal(str(data["wind"].get("gust", 0)))
    snow_mm = data.get("snow", {}).get("1h", 0)
    snow_inches = Decimal(str(snow_mm * 0.0394))
    rain_mm = data.get("rain", {}).get("1h", 0)
    rain_inches = Decimal(str(rain_mm * 0.0394))
    conditions = data.get("weather", [{}])

    snapshot = WeatherSnapshot.objects.create(
        property=config.property,
        timestamp=timezone.now(),
        temperature_f=temperature_f,
        feels_like_f=feels_like_f,
        humidity=humidity,
        wind_speed_mph=wind_speed_mph,
        wind_gust_mph=wind_gust_mph,
        conditions=conditions,
        snow_inches=snow_inches,
        rain_inches=rain_inches,
        raw_data=data,
    )

    logger.info(
        "Created weather snapshot %s for property %s",
        snapshot.id,
        config.property,
    )

    # Dispatch threshold check
    async_task(
        "apps.weather.tasks.check_weather_thresholds",
        str(snapshot.id),
    )

    return str(snapshot.id)


def check_weather_thresholds(snapshot_id):
    """Compare a snapshot against config thresholds and create WeatherAlerts if exceeded.

    Args:
        snapshot_id: UUID (as string) of the WeatherSnapshot.
    """
    from django_q.tasks import async_task

    from .models import WeatherAlert, WeatherMonitorConfig, WeatherSnapshot

    try:
        snapshot = WeatherSnapshot.objects.select_related("property").get(id=snapshot_id)
    except WeatherSnapshot.DoesNotExist:
        logger.warning("WeatherSnapshot %s not found", snapshot_id)
        return []

    try:
        config = WeatherMonitorConfig.objects.get(property=snapshot.property)
    except WeatherMonitorConfig.DoesNotExist:
        logger.warning("No WeatherMonitorConfig for property %s", snapshot.property)
        return []

    alerts_created = []

    # Snow threshold
    if snapshot.snow_inches and snapshot.snow_inches > config.snow_threshold_inches:
        alert = _create_alert(
            snapshot=snapshot,
            alert_type="snow",
            title=f"Snow Alert: {snapshot.property.name}",
            message=(
                f"Snow accumulation of {snapshot.snow_inches}\" detected, "
                f"exceeding threshold of {config.snow_threshold_inches}\". "
                f"Current temperature: {snapshot.temperature_f}\u00b0F."
            ),
        )
        alerts_created.append(str(alert.id))

    # Wind threshold
    if snapshot.wind_speed_mph and snapshot.wind_speed_mph > config.wind_threshold_mph:
        alert = _create_alert(
            snapshot=snapshot,
            alert_type="wind",
            title=f"High Wind Alert: {snapshot.property.name}",
            message=(
                f"Wind speed of {snapshot.wind_speed_mph} mph detected, "
                f"exceeding threshold of {config.wind_threshold_mph} mph. "
                f"Gusts up to {snapshot.wind_gust_mph} mph."
            ),
        )
        alerts_created.append(str(alert.id))

    # Extreme cold threshold
    if snapshot.temperature_f is not None and snapshot.temperature_f < config.temp_low_threshold_f:
        alert = _create_alert(
            snapshot=snapshot,
            alert_type="extreme_cold",
            title=f"Extreme Cold Alert: {snapshot.property.name}",
            message=(
                f"Temperature of {snapshot.temperature_f}\u00b0F detected, "
                f"below threshold of {config.temp_low_threshold_f}\u00b0F. "
                f"Feels like {snapshot.feels_like_f}\u00b0F."
            ),
        )
        alerts_created.append(str(alert.id))

    # Extreme heat threshold
    if snapshot.temperature_f is not None and snapshot.temperature_f > config.temp_high_threshold_f:
        alert = _create_alert(
            snapshot=snapshot,
            alert_type="extreme_heat",
            title=f"Extreme Heat Alert: {snapshot.property.name}",
            message=(
                f"Temperature of {snapshot.temperature_f}\u00b0F detected, "
                f"exceeding threshold of {config.temp_high_threshold_f}\u00b0F. "
                f"Feels like {snapshot.feels_like_f}\u00b0F."
            ),
        )
        alerts_created.append(str(alert.id))

    # Update snapshot alert_type with the first triggered alert (if any)
    if alerts_created:
        first_alert = WeatherAlert.objects.get(id=alerts_created[0])
        snapshot.alert_type = first_alert.alert_type
        snapshot.save(update_fields=["alert_type"])

    # Dispatch notifications for each alert
    for alert_id in alerts_created:
        async_task(
            "apps.weather.tasks.send_weather_alert_notifications",
            alert_id,
        )

    logger.info(
        "Threshold check for snapshot %s: %d alert(s) created",
        snapshot_id,
        len(alerts_created),
    )
    return alerts_created


def _create_alert(snapshot, alert_type, title, message):
    """Helper to create a WeatherAlert from a snapshot."""
    from .models import WeatherAlert

    severity = _determine_severity(snapshot, alert_type)
    return WeatherAlert.objects.create(
        property=snapshot.property,
        snapshot=snapshot,
        alert_type=alert_type,
        severity=severity,
        title=title,
        message=message,
        auto_generated=True,
    )


def _determine_severity(snapshot, alert_type):
    """Determine alert severity based on conditions.

    Returns 'emergency', 'warning', or 'watch'.
    """
    from .models import WeatherMonitorConfig

    try:
        config = WeatherMonitorConfig.objects.get(property=snapshot.property)
    except WeatherMonitorConfig.DoesNotExist:
        return "watch"

    if alert_type == "snow":
        if snapshot.snow_inches >= config.snow_threshold_inches * 3:
            return "emergency"
        elif snapshot.snow_inches >= config.snow_threshold_inches * 2:
            return "warning"
        return "watch"

    if alert_type == "wind":
        if snapshot.wind_speed_mph >= config.wind_threshold_mph * Decimal("1.5"):
            return "emergency"
        elif snapshot.wind_speed_mph >= config.wind_threshold_mph * Decimal("1.25"):
            return "warning"
        return "watch"

    if alert_type == "extreme_cold":
        if snapshot.temperature_f <= config.temp_low_threshold_f - 20:
            return "emergency"
        elif snapshot.temperature_f <= config.temp_low_threshold_f - 10:
            return "warning"
        return "watch"

    if alert_type == "extreme_heat":
        if snapshot.temperature_f >= config.temp_high_threshold_f + 15:
            return "emergency"
        elif snapshot.temperature_f >= config.temp_high_threshold_f + 8:
            return "warning"
        return "watch"

    return "watch"


def send_weather_alert_notifications(alert_id):
    """Create a Notification for each tenant with an active lease at the property.

    Args:
        alert_id: UUID (as string) of the WeatherAlert.
    """
    from apps.communications.models import Notification
    from apps.leases.models import Lease

    from .models import WeatherAlert

    try:
        alert = WeatherAlert.objects.select_related("property").get(id=alert_id)
    except WeatherAlert.DoesNotExist:
        logger.warning("WeatherAlert %s not found", alert_id)
        return 0

    # Find all tenants with active leases at units belonging to this property
    active_leases = Lease.objects.filter(
        unit__property=alert.property,
        status="active",
    ).select_related("tenant")

    notifications_created = 0
    for lease in active_leases:
        Notification.objects.create(
            recipient=lease.tenant,
            channel="in_app",
            category="weather",
            title=alert.title,
            body=alert.message,
        )
        notifications_created += 1

    # Mark alert as notification sent
    alert.notification_sent = True
    alert.sent_at = timezone.now()
    alert.save(update_fields=["notification_sent", "sent_at"])

    logger.info(
        "Sent %d notification(s) for alert %s",
        notifications_created,
        alert_id,
    )
    return notifications_created


def cleanup_old_snapshots(days=90):
    """Delete weather snapshots older than the specified number of days.

    Args:
        days: Number of days to retain. Defaults to 90.
    """
    from .models import WeatherSnapshot

    cutoff = timezone.now() - timedelta(days=days)
    result = WeatherSnapshot.objects.filter(timestamp__lt=cutoff).delete()
    deleted_count = result[0] if result else 0

    logger.info(
        "Cleaned up %d weather snapshot(s) older than %d days",
        deleted_count,
        days,
    )
    return deleted_count
