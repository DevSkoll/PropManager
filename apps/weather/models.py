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
