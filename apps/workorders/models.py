from django.conf import settings
from django.db import models

from apps.core.models import AuditMixin, TimeStampedModel


class WorkOrder(TimeStampedModel, AuditMixin):
    STATUS_CHOICES = [
        ("created", "Created"),
        ("verified", "Verified"),
        ("assigned", "Assigned"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("closed", "Closed"),
    ]
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("emergency", "Emergency"),
    ]
    CATEGORY_CHOICES = [
        ("plumbing", "Plumbing"),
        ("electrical", "Electrical"),
        ("hvac", "HVAC"),
        ("appliance", "Appliance"),
        ("structural", "Structural"),
        ("pest_control", "Pest Control"),
        ("landscaping", "Landscaping"),
        ("cleaning", "Cleaning"),
        ("general", "General"),
        ("other", "Other"),
    ]

    VALID_TRANSITIONS = {
        "created": ["verified", "closed"],
        "verified": ["assigned", "closed"],
        "assigned": ["in_progress", "closed"],
        "in_progress": ["completed", "closed"],
        "completed": ["closed"],
        "closed": [],
    }

    title = models.CharField(max_length=200)
    description = models.TextField()
    unit = models.ForeignKey("properties.Unit", on_delete=models.CASCADE, related_name="work_orders")
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="reported_work_orders"
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="created", db_index=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="medium", db_index=True)
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, default="general")
    scheduled_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    cost_estimate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"WO-{self.pk.__str__()[:8]}: {self.title}"

    def can_transition_to(self, new_status):
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])


class ContractorAssignment(TimeStampedModel):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name="assignments")
    contractor_name = models.CharField(max_length=200)
    contractor_phone = models.CharField(max_length=20, blank=True, default="")
    contractor_email = models.EmailField(blank=True, default="")
    access_token = models.OneToOneField(
        "accounts.ContractorAccessToken",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignment",
    )
    notes = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.contractor_name} -> {self.work_order}"


class WorkOrderNote(TimeStampedModel):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name="notes")
    author_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="work_order_notes"
    )
    author_contractor_token = models.ForeignKey(
        "accounts.ContractorAccessToken",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="work_order_notes",
    )
    text = models.TextField()
    is_internal = models.BooleanField(default=False)

    def __str__(self):
        author = self.author_user or self.author_contractor_token
        return f"Note on {self.work_order} by {author}"


class WorkOrderImage(TimeStampedModel):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="workorder_images/%Y/%m/")
    caption = models.CharField(max_length=255, blank=True, default="")
    uploaded_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    uploaded_by_contractor_token = models.ForeignKey(
        "accounts.ContractorAccessToken",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"Image for {self.work_order}"
