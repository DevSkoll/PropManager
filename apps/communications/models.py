from django.conf import settings
from django.db import models

from apps.core.models import AuditMixin, TimeStampedModel


class MessageThread(TimeStampedModel):
    subject = models.CharField(max_length=255)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="message_threads"
    )
    related_work_order = models.ForeignKey(
        "workorders.WorkOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="message_threads",
    )
    is_closed = models.BooleanField(default=False)

    def __str__(self):
        return self.subject

    @property
    def last_message(self):
        return self.messages.order_by("-created_at").first()


class Message(TimeStampedModel):
    thread = models.ForeignKey(MessageThread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="sent_messages"
    )
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message from {self.sender} in {self.thread}"


class Notification(TimeStampedModel):
    CHANNEL_CHOICES = [
        ("in_app", "In-App"),
        ("email", "Email"),
        ("sms", "SMS"),
    ]
    CATEGORY_CHOICES = [
        ("billing", "Billing"),
        ("work_order", "Work Order"),
        ("lease", "Lease"),
        ("weather", "Weather"),
        ("announcement", "Announcement"),
        ("message", "Message"),
        ("system", "System"),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default="in_app")
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, default="system")
    title = models.CharField(max_length=255)
    body = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    action_url = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} -> {self.recipient}"


class Announcement(TimeStampedModel, AuditMixin):
    title = models.CharField(max_length=255)
    body = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="announcements"
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="announcements",
        help_text="Leave blank for all properties",
    )
    is_published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title
