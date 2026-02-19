from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import AuditMixin, TimeStampedModel


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

CHANNEL_CHOICES = [
    ("email", "Email"),
    ("sms", "SMS"),
    ("both", "Both"),
    ("webhook", "Webhook"),
]

CHANNEL_WITH_NONE_CHOICES = [
    ("email", "Email"),
    ("sms", "SMS"),
    ("both", "Both"),
    ("none", "None"),
]

EVENT_TYPE_CHOICES = [
    ("new_work_order", "New Work Order"),
    ("payment_received", "Payment Received"),
    ("new_message", "New Message"),
    ("new_document", "New Document"),
    ("lease_expiring", "Lease Expiring"),
    ("invoice_overdue", "Invoice Overdue"),
    ("weather_alert", "Weather Alert"),
    ("new_tenant", "New Tenant"),
    ("reward_earned", "Reward Earned"),
]

CATEGORY_CHOICES = [
    ("weather_updates", "Weather Updates"),
    ("new_invoice", "New Invoice"),
    ("past_due_balance", "Past Due Balance"),
    ("messages", "Messages"),
    ("announcements", "Announcements"),
    ("rewards", "Rewards"),
]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class NotificationGroup(TimeStampedModel, AuditMixin):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class GroupContact(TimeStampedModel):
    group = models.ForeignKey(
        NotificationGroup, on_delete=models.CASCADE, related_name="contacts"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        limit_choices_to=models.Q(role__in=["admin", "staff"]),
        related_name="notification_contacts",
    )
    external_name = models.CharField(max_length=200, blank=True, default="")
    external_email = models.EmailField(blank=True, default="")
    external_phone = models.CharField(max_length=20, blank=True, default="")
    service_name = models.CharField(max_length=200, blank=True, default="")
    webhook_url = models.URLField(max_length=500, blank=True, default="")
    channel = models.CharField(max_length=7, choices=CHANNEL_CHOICES, default="email")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["group", "user"],
                condition=models.Q(user__isnull=False),
                name="unique_user_per_group",
            )
        ]

    def __str__(self):
        return self.display_name()

    def display_name(self):
        if self.user:
            return self.user.get_full_name() or self.user.username
        if self.service_name:
            return self.service_name
        return self.external_name

    def resolved_email(self):
        if self.user:
            return self.user.email
        return self.external_email

    def resolved_phone(self):
        if self.user:
            return self.user.phone_number
        return self.external_phone

    def clean(self):
        super().clean()
        if self.channel == "webhook":
            if not self.service_name:
                raise ValidationError(
                    {"service_name": "Webhook contacts must have a service name."}
                )
            if not self.webhook_url:
                raise ValidationError(
                    {"webhook_url": "Webhook contacts must have a URL."}
                )
        elif not self.user:
            if not self.external_name:
                raise ValidationError(
                    {"external_name": "External contacts must have a name."}
                )
            if not self.external_email and not self.external_phone:
                raise ValidationError(
                    "External contacts must have at least an email or phone number."
                )


class EventTypeSubscription(TimeStampedModel):
    group = models.ForeignKey(
        NotificationGroup, on_delete=models.CASCADE, related_name="subscriptions"
    )
    event_type = models.CharField(
        max_length=30, choices=EVENT_TYPE_CHOICES, db_index=True
    )

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("group", "event_type")]

    def __str__(self):
        return f"{self.group.name} → {self.get_event_type_display()}"


class TenantNotificationPreference(TimeStampedModel):
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "tenant"},
        related_name="notification_preferences",
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    channel = models.CharField(
        max_length=5, choices=CHANNEL_WITH_NONE_CHOICES, default="email"
    )

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("tenant", "category")]

    def __str__(self):
        return f"{self.tenant} — {self.get_category_display()} → {self.get_channel_display()}"


class ReminderLog(TimeStampedModel):
    REMINDER_CHANNEL_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
    ]

    invoice = models.ForeignKey(
        "billing.Invoice", on_delete=models.CASCADE, related_name="reminder_logs"
    )
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_reminders",
    )
    channel = models.CharField(max_length=5, choices=REMINDER_CHANNEL_CHOICES)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"Reminder for {self.invoice} at {self.sent_at}"
