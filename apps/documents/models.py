from django.conf import settings
from django.db import models

from apps.core.models import AuditMixin, TimeStampedModel


class DocumentCategory(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name_plural = "Document Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Document(TimeStampedModel, AuditMixin):
    DOCUMENT_TYPE_CHOICES = [
        ("lease", "Lease Agreement"),
        ("notice", "Notice"),
        ("inspection", "Inspection Report"),
        ("receipt", "Receipt"),
        ("insurance", "Insurance"),
        ("photo", "Photo"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=255)
    document_type = models.CharField(max_length=15, choices=DOCUMENT_TYPE_CHOICES, default="other")
    category = models.ForeignKey(
        DocumentCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents"
    )
    file = models.FileField(upload_to="documents/%Y/%m/")
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes")
    mime_type = models.CharField(max_length=100, blank=True, default="")
    property = models.ForeignKey(
        "properties.Property", on_delete=models.SET_NULL, null=True, blank=True, related_name="documents"
    )
    unit = models.ForeignKey(
        "properties.Unit", on_delete=models.SET_NULL, null=True, blank=True, related_name="documents"
    )
    lease = models.ForeignKey(
        "leases.Lease", on_delete=models.SET_NULL, null=True, blank=True, related_name="documents"
    )
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents"
    )
    work_order = models.ForeignKey(
        "workorders.WorkOrder", on_delete=models.SET_NULL, null=True, blank=True, related_name="documents"
    )
    is_tenant_visible = models.BooleanField(default=False, db_index=True)
    description = models.TextField(blank=True, default="")

    def __str__(self):
        return self.title
