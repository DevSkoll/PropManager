import logging
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_template_context(snapshot, alert):
    """Build the dict of template variables from a snapshot and alert."""
    return {
        "property_name": snapshot.property.name,
        "property_address": snapshot.property.full_address(),
        "temperature": str(snapshot.temperature_f or "N/A"),
        "feels_like": str(snapshot.feels_like_f or "N/A"),
        "humidity": str(snapshot.humidity or "N/A"),
        "wind_speed": str(snapshot.wind_speed_mph or "0"),
        "wind_gust": str(snapshot.wind_gust_mph or "0"),
        "snow_inches": str(snapshot.snow_inches or "0"),
        "rain_inches": str(snapshot.rain_inches or "0"),
        "alert_type": alert.get_alert_type_display(),
        "severity": alert.get_severity_display(),
        "timestamp": snapshot.timestamp.strftime("%B %d, %Y at %I:%M %p"),
    }


def render_template(template_str, context):
    """Safely render a user-provided template string with context variables.

    Uses str.format_map with a SafeDict fallback so unknown placeholders
    render as-is rather than raising KeyError.
    """

    class SafeDict(dict):
        def __missing__(self, key):
            return "{" + key + "}"

    try:
        return template_str.format_map(SafeDict(context))
    except (ValueError, IndexError) as exc:
        logger.warning("Template rendering error: %s", exc)
        return template_str


def find_matching_rules(alert):
    """Find active WeatherNotificationRules that match a given alert."""
    from .models import WeatherNotificationRule

    rules = WeatherNotificationRule.objects.filter(
        alert_type=alert.alert_type,
        is_active=True,
    ).filter(
        Q(property=alert.property) | Q(property__isnull=True)
    )

    matched = []
    for rule in rules:
        if rule.severity == "all" or rule.severity == alert.severity:
            matched.append(rule)

    return matched


def is_rule_in_cooldown(rule, property_obj):
    """Check whether the rule has fired recently for this property."""
    from .models import WeatherRuleDispatchLog

    if rule.cooldown_hours == 0:
        return False

    cutoff = timezone.now() - timedelta(hours=rule.cooldown_hours)
    return WeatherRuleDispatchLog.objects.filter(
        rule=rule,
        property=property_obj,
        dispatched_at__gte=cutoff,
    ).exists()
