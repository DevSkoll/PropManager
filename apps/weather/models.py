from django.db import models

from apps.core.models import TimeStampedModel


class WeatherMonitorConfig(TimeStampedModel):
    property = models.OneToOneField(
        "properties.Property", on_delete=models.CASCADE, related_name="weather_config"
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    is_active = models.BooleanField(default=True)
    polling_interval_hours = models.PositiveSmallIntegerField(default=2)
    snow_threshold_inches = models.DecimalField(max_digits=5, decimal_places=1, default=2.0)
    wind_threshold_mph = models.DecimalField(max_digits=5, decimal_places=1, default=40.0)
    temp_low_threshold_f = models.DecimalField(max_digits=5, decimal_places=1, default=10.0)
    temp_high_threshold_f = models.DecimalField(max_digits=5, decimal_places=1, default=100.0)

    def __str__(self):
        return f"Weather Config: {self.property}"


class WeatherSnapshot(TimeStampedModel):
    ALERT_TYPE_CHOICES = [
        ("snow", "Snow"),
        ("storm", "Storm"),
        ("extreme_heat", "Extreme Heat"),
        ("extreme_cold", "Extreme Cold"),
        ("wind", "High Wind"),
        ("flood", "Flood"),
    ]

    property = models.ForeignKey(
        "properties.Property", on_delete=models.CASCADE, related_name="weather_snapshots"
    )
    timestamp = models.DateTimeField(db_index=True)
    temperature_f = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    feels_like_f = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    humidity = models.PositiveSmallIntegerField(null=True, blank=True)
    wind_speed_mph = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    wind_gust_mph = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    conditions = models.JSONField(default=dict)
    snow_inches = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    rain_inches = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    alert_type = models.CharField(
        max_length=15, choices=ALERT_TYPE_CHOICES, null=True, blank=True
    )
    raw_data = models.JSONField(default=dict)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"Weather @ {self.property} on {self.timestamp}"


class WeatherAlert(TimeStampedModel):
    ALERT_TYPE_CHOICES = WeatherSnapshot.ALERT_TYPE_CHOICES
    SEVERITY_CHOICES = [
        ("watch", "Watch"),
        ("warning", "Warning"),
        ("emergency", "Emergency"),
    ]

    property = models.ForeignKey(
        "properties.Property", on_delete=models.CASCADE, related_name="weather_alerts"
    )
    snapshot = models.ForeignKey(
        WeatherSnapshot, on_delete=models.SET_NULL, null=True, blank=True, related_name="alerts"
    )
    alert_type = models.CharField(max_length=15, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="watch")
    title = models.CharField(max_length=255)
    message = models.TextField()
    auto_generated = models.BooleanField(default=True)
    notification_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({self.severity})"


class WeatherNotificationRule(TimeStampedModel):
    """Admin-created rule that defines when and how to notify tenants about weather conditions."""

    RULE_SEVERITY_CHOICES = [
        ("all", "All Severities"),
        ("watch", "Watch"),
        ("warning", "Warning"),
        ("emergency", "Emergency"),
    ]

    name = models.CharField(
        max_length=200,
        help_text="Descriptive name for this rule (e.g., 'Snow Plowing Reminder')",
    )
    alert_type = models.CharField(
        max_length=15,
        choices=WeatherSnapshot.ALERT_TYPE_CHOICES,
        db_index=True,
        help_text="The weather condition that triggers this rule.",
    )
    severity = models.CharField(
        max_length=10,
        choices=RULE_SEVERITY_CHOICES,
        default="all",
        help_text="Minimum severity level to trigger (or 'All' for any).",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="weather_notification_rules",
        help_text="Leave blank to apply to all properties.",
    )
    subject_template = models.CharField(
        max_length=255,
        help_text="Notification subject. Use {property_name}, {alert_type}, etc.",
    )
    message_template = models.TextField(
        help_text=(
            "Notification body. Available variables: {property_name}, {property_address}, "
            "{temperature}, {feels_like}, {humidity}, {wind_speed}, {wind_gust}, "
            "{snow_inches}, {rain_inches}, {alert_type}, {severity}, {timestamp}"
        ),
    )
    is_active = models.BooleanField(default=True, db_index=True)
    cooldown_hours = models.PositiveSmallIntegerField(
        default=24,
        help_text="Hours before this rule can fire again for the same property.",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        prop_label = self.property.name if self.property else "All Properties"
        return f"{self.name} ({self.get_alert_type_display()} / {prop_label})"


class WeatherRuleDispatchLog(TimeStampedModel):
    """Tracks each time a notification rule fires, for cooldown/deduplication."""

    rule = models.ForeignKey(
        WeatherNotificationRule,
        on_delete=models.CASCADE,
        related_name="dispatch_logs",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="weather_rule_dispatches",
    )
    alert = models.ForeignKey(
        WeatherAlert,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rule_dispatches",
    )
    snapshot = models.ForeignKey(
        WeatherSnapshot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    rendered_subject = models.CharField(max_length=255)
    rendered_message = models.TextField()
    tenants_notified = models.PositiveIntegerField(default=0)
    dispatched_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-dispatched_at"]
        indexes = [
            models.Index(fields=["rule", "property", "-dispatched_at"]),
        ]

    def __str__(self):
        return f"Dispatch: {self.rule.name} @ {self.property} ({self.dispatched_at})"
