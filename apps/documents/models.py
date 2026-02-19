from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import AuditMixin, TimeStampedModel


class DocumentCategory(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name_plural = "Document Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class DocumentFolder(TimeStampedModel, AuditMixin):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    unit = models.ForeignKey(
        "properties.Unit", on_delete=models.CASCADE, related_name="document_folders"
    )
    lease = models.ForeignKey(
        "leases.Lease", on_delete=models.SET_NULL, null=True, blank=True, related_name="document_folders"
    )
    is_tenant_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("name", "unit")]

    def __str__(self):
        return f"{self.name} ({self.unit})"


class DocumentManager(models.Manager):
    """Default manager that excludes soft-deleted documents."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


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

    UPLOADED_BY_ROLE_CHOICES = [
        ("admin", "Admin"),
        ("tenant", "Tenant"),
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

    # New fields
    folder = models.ForeignKey(
        DocumentFolder, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents"
    )
    uploaded_by_role = models.CharField(
        max_length=10, choices=UPLOADED_BY_ROLE_CHOICES, default="admin"
    )
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="deleted_documents",
    )
    is_locked = models.BooleanField(
        default=False, help_text="Locked documents cannot be modified or deleted."
    )
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="locked_documents",
    )
    locked_at = models.DateTimeField(null=True, blank=True)

    objects = DocumentManager()       # default: excludes soft-deleted
    all_objects = models.Manager()    # includes soft-deleted

    def __str__(self):
        return self.title

    def soft_delete(self, user=None):
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=["deleted_at", "deleted_by"])

    def restore(self):
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=["deleted_at", "deleted_by"])

    def lock(self, user):
        self.is_locked = True
        self.locked_by = user
        self.locked_at = timezone.now()
        self.save(update_fields=["is_locked", "locked_by", "locked_at"])

    def unlock(self):
        self.is_locked = False
        self.locked_by = None
        self.locked_at = None
        self.save(update_fields=["is_locked", "locked_by", "locked_at"])

    # ------------------------------------------------------------------
    # Preview helpers
    # ------------------------------------------------------------------

    IMAGE_MIME_TYPES = {
        "image/jpeg", "image/png", "image/gif", "image/bmp", "image/webp", "image/tiff",
    }
    PDF_MIME_TYPES = {"application/pdf"}
    TEXT_MIME_TYPES = {"text/plain", "text/csv"}

    def preview_type(self):
        """Return 'image', 'pdf', 'text', or None based on MIME type."""
        mt = (self.mime_type or "").lower()
        if mt in self.IMAGE_MIME_TYPES:
            return "image"
        if mt in self.PDF_MIME_TYPES:
            return "pdf"
        if mt in self.TEXT_MIME_TYPES:
            return "text"
        return None

    def is_previewable(self):
        return self.preview_type() is not None
