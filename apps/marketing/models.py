import secrets

from django.conf import settings
from django.db import models

from apps.core.models import AuditMixin, TimeStampedModel


class Campaign(TimeStampedModel, AuditMixin):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("sending", "Sending"),
        ("sent", "Sent"),
        ("cancelled", "Cancelled"),
    ]

    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    body_html = models.TextField(blank=True, default="")
    body_text = models.TextField(blank=True, default="")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="draft", db_index=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="campaigns"
    )

    def __str__(self):
        return f"{self.name} ({self.status})"

    @property
    def recipient_count(self):
        return self.recipients.count()

    @property
    def open_rate(self):
        total = self.recipients.filter(status__in=["sent", "delivered", "opened", "clicked"]).count()
        if total == 0:
            return 0
        opened = self.recipients.filter(status__in=["opened", "clicked"]).count()
        return round((opened / total) * 100, 1)


class CampaignSegment(TimeStampedModel):
    FILTER_TYPE_CHOICES = [
        ("all", "All Tenants"),
        ("by_property", "By Property"),
        ("by_lease_status", "By Lease Status"),
        ("by_move_in_date", "By Move-in Date"),
        ("custom", "Custom Selection"),
    ]

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="segments")
    filter_type = models.CharField(max_length=20, choices=FILTER_TYPE_CHOICES)
    filter_value = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.campaign} - {self.get_filter_type_display()}"


class CampaignRecipient(TimeStampedModel):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("delivered", "Delivered"),
        ("opened", "Opened"),
        ("clicked", "Clicked"),
        ("bounced", "Bounced"),
        ("failed", "Failed"),
    ]

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="recipients")
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="campaign_recipients"
    )
    email = models.EmailField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="pending", db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("campaign", "tenant")]

    def __str__(self):
        return f"{self.campaign} -> {self.email} ({self.status})"


class CampaignLink(TimeStampedModel):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="links")
    original_url = models.URLField(max_length=500)
    tracking_token = models.CharField(max_length=64, unique=True, db_index=True)
    click_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Link: {self.original_url[:50]} ({self.click_count} clicks)"

    def save(self, *args, **kwargs):
        if not self.tracking_token:
            self.tracking_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)
