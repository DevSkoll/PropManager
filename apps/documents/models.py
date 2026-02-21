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


# =============================================================================
# eDocument Models - Template-based document signing system
# =============================================================================


class EDocumentTemplate(TimeStampedModel, AuditMixin):
    """Reusable document templates written in markdown with signature tags."""

    TEMPLATE_TYPE_CHOICES = [
        ("lease", "Lease Agreement"),
        ("pet_agreement", "Pet Agreement"),
        ("termination", "Lease Termination"),
        ("addendum", "Lease Addendum"),
        ("notice", "Notice"),
        ("disclosure", "Disclosure"),
        ("other", "Other"),
    ]

    name = models.CharField(max_length=200)
    template_type = models.CharField(
        max_length=20, choices=TEMPLATE_TYPE_CHOICES, default="other"
    )
    description = models.TextField(blank=True, default="")
    content = models.TextField(
        help_text="Markdown content with {{variables}} and [SIGNATURE:Role] tags"
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edocument_templates",
        help_text="If set, template is only available for this property",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "eDocument Template"
        verbose_name_plural = "eDocument Templates"

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


class EDocument(TimeStampedModel, AuditMixin):
    """Individual document instance created from a template or scratch."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Pending Signatures"),
        ("partial", "Partially Signed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    title = models.CharField(max_length=255)
    template = models.ForeignKey(
        EDocumentTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
        help_text="Source template (if created from template)",
    )
    content = models.TextField(
        help_text="Markdown content (frozen copy from template or custom)"
    )
    rendered_html = models.TextField(
        blank=True,
        default="",
        help_text="Rendered HTML with variables substituted",
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default="draft", db_index=True
    )

    # Attachments - can link to lease, tenant, and/or property
    lease = models.ForeignKey(
        "leases.Lease",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edocuments",
    )
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edocuments_received",
        help_text="Primary tenant for this document",
    )
    edoc_property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edocuments",
    )

    # Lifecycle timestamps
    sent_at = models.DateTimeField(
        null=True, blank=True, help_text="When sent to signers"
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="When all signatures collected"
    )

    # Final output
    final_pdf = models.FileField(
        upload_to="edocuments/signed/%Y/%m/",
        null=True,
        blank=True,
        help_text="Generated PDF after completion",
    )
    is_locked = models.BooleanField(
        default=False, help_text="Document is read-only after completion"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "eDocument"
        verbose_name_plural = "eDocuments"

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def is_fully_signed(self):
        """Check if all signers have completed signing."""
        if not self.signers.exists():
            return False
        return not self.signers.filter(signed_at__isnull=True).exists()

    @property
    def signature_progress(self):
        """Return signing progress stats."""
        total = self.signers.count()
        signed = self.signers.filter(signed_at__isnull=False).count()
        percent = int((signed / total) * 100) if total > 0 else 0
        return {"total": total, "signed": signed, "percent": percent}

    def check_completion(self):
        """Check if document is complete and update status if so."""
        if self.is_fully_signed and self.status != "completed":
            self.status = "completed"
            self.completed_at = timezone.now()
            self.is_locked = True
            self.save(update_fields=["status", "completed_at", "is_locked"])

            # Generate PDF asynchronously (or sync if no task queue)
            self._generate_pdf()

            return True
        return False

    def _generate_pdf(self):
        """Generate PDF for the completed document."""
        try:
            from .services.pdf import generate_edocument_pdf
            generate_edocument_pdf(self)
        except ImportError:
            # WeasyPrint not installed, skip PDF generation
            import logging
            logging.getLogger(__name__).warning(
                f"Could not generate PDF for eDocument {self.pk}: WeasyPrint not installed"
            )


class EDocumentSigner(TimeStampedModel):
    """A signer assigned to an eDocument with their role."""

    ROLE_CHOICES = [
        ("landlord", "Landlord"),
        ("tenant", "Tenant"),
        ("tenant2", "Tenant 2"),
        ("tenant3", "Tenant 3"),
        ("tenant4", "Tenant 4"),
        ("cosigner", "Co-Signer"),
    ]

    document = models.ForeignKey(
        EDocument, on_delete=models.CASCADE, related_name="signers"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edocument_signers",
        help_text="Linked user account for portal access",
    )
    name = models.CharField(max_length=200)
    email = models.EmailField()

    # Signature capture (final signature after all blocks signed)
    signature_image = models.TextField(
        blank=True, default="", help_text="Base64 encoded signature image"
    )
    signed_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["role"]
        unique_together = [("document", "role")]
        verbose_name = "eDocument Signer"
        verbose_name_plural = "eDocument Signers"

    def __str__(self):
        status = "Signed" if self.signed_at else "Pending"
        return f"{self.name} ({self.get_role_display()}) - {status}"

    @property
    def is_signed(self):
        return self.signed_at is not None

    @property
    def pending_blocks_count(self):
        """Count of signature blocks not yet signed by this signer."""
        return self.blocks.filter(signed_at__isnull=True).count()

    @property
    def all_blocks_signed(self):
        """Check if signer has signed all their blocks."""
        if not self.blocks.exists():
            return False
        return not self.blocks.filter(signed_at__isnull=True).exists()


class EDocumentSignatureBlock(TimeStampedModel):
    """Individual signature or initials block within a document."""

    BLOCK_TYPE_CHOICES = [
        ("signature", "Signature"),
        ("initials", "Initials"),
    ]

    document = models.ForeignKey(
        EDocument, on_delete=models.CASCADE, related_name="signature_blocks"
    )
    signer = models.ForeignKey(
        EDocumentSigner, on_delete=models.CASCADE, related_name="blocks"
    )
    block_type = models.CharField(max_length=10, choices=BLOCK_TYPE_CHOICES)
    block_order = models.PositiveIntegerField(
        help_text="Order of appearance in document (parsed from markdown)"
    )

    # Signature capture
    image = models.TextField(
        blank=True, default="", help_text="Base64 encoded signature/initials image"
    )
    signed_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["block_order"]
        verbose_name = "eDocument Signature Block"
        verbose_name_plural = "eDocument Signature Blocks"

    def __str__(self):
        status = "Signed" if self.signed_at else "Pending"
        return f"{self.get_block_type_display()} #{self.block_order} - {self.signer.name} ({status})"

    @property
    def is_signed(self):
        return self.signed_at is not None


class EDocumentFillableBlock(TimeStampedModel):
    """Fillable text field within a document for dynamic content."""

    ROLE_CHOICES = [
        ("landlord", "Landlord"),
        ("tenant", "Tenant"),
        ("tenant2", "Tenant 2"),
        ("tenant3", "Tenant 3"),
        ("tenant4", "Tenant 4"),
        ("cosigner", "Co-Signer"),
    ]

    document = models.ForeignKey(
        EDocument, on_delete=models.CASCADE, related_name="fillable_blocks"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    block_order = models.PositiveIntegerField(
        help_text="Order of appearance in document (parsed from markdown)"
    )

    # Filled content
    content = models.TextField(
        blank=True, default="", help_text="Text content filled in by signer"
    )
    filled_at = models.DateTimeField(null=True, blank=True)
    filled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edocument_fillable_blocks",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["block_order"]
        unique_together = [("document", "block_order")]
        verbose_name = "eDocument Fillable Block"
        verbose_name_plural = "eDocument Fillable Blocks"

    def __str__(self):
        status = "Filled" if self.filled_at else "Pending"
        preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"Fillable #{self.block_order} ({self.get_role_display()}) - {status}: {preview}"

    @property
    def is_filled(self):
        return self.filled_at is not None
