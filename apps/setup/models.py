from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class SetupConfiguration(models.Model):
    """
    Singleton model to track setup wizard state and completion.
    Only one record should exist (pk=1).
    """

    is_complete = models.BooleanField(default=False, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="setup_completions",
    )
    steps_completed = models.JSONField(
        default=dict,
        help_text="Dict of step_name -> {completed_at, skipped, warnings}",
    )
    setup_version = models.CharField(max_length=20, default="1.0.0")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Setup Configuration"
        verbose_name_plural = "Setup Configuration"

    def __str__(self):
        return f"Setup {'Complete' if self.is_complete else 'Incomplete'}"

    @classmethod
    def get_instance(cls):
        """Get or create the singleton instance."""
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance

    @classmethod
    def is_setup_complete(cls):
        """Check if setup has been completed."""
        try:
            instance = cls.objects.get(pk=1)
            return instance.is_complete
        except cls.DoesNotExist:
            return False

    def mark_step_complete(self, step_name, skipped=False, warnings=None):
        """Mark a step as completed."""
        self.steps_completed[step_name] = {
            "completed_at": timezone.now().isoformat(),
            "skipped": skipped,
            "warnings": warnings or [],
        }
        self.save(update_fields=["steps_completed", "updated_at"])

    def is_step_complete(self, step_name):
        """Check if a specific step has been completed."""
        return step_name in self.steps_completed

    def get_step_status(self, step_name):
        """Get the status of a specific step."""
        return self.steps_completed.get(step_name, None)

    def finalize(self, user=None):
        """Mark setup as fully complete."""
        self.is_complete = True
        self.completed_at = timezone.now()
        self.completed_by = user
        self.save()

    def reset(self):
        """Reset setup to incomplete state (for testing/debugging)."""
        self.is_complete = False
        self.completed_at = None
        self.completed_by = None
        self.steps_completed = {}
        self.save()


class CSVImportLog(TimeStampedModel):
    """Audit log for CSV import operations during setup."""

    IMPORT_TYPE_CHOICES = [
        ("properties", "Properties"),
        ("units", "Units"),
        ("tenants", "Tenants"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    import_type = models.CharField(max_length=20, choices=IMPORT_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    file_name = models.CharField(max_length=255)
    total_rows = models.PositiveIntegerField(default=0)
    successful_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)
    errors = models.JSONField(
        default=list, help_text="List of error messages with row numbers"
    )
    warnings = models.JSONField(
        default=list, help_text="List of warning messages with row numbers"
    )
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="csv_imports",
    )

    class Meta:
        verbose_name = "CSV Import Log"
        verbose_name_plural = "CSV Import Logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_import_type_display()} import - {self.status}"


# Wizard step configuration
WIZARD_STEPS = [
    {
        "key": "welcome",
        "title": "Welcome",
        "description": "Introduction to PropManager setup",
        "icon": "bi-house-door",
        "skip_allowed": False,
        "criticality": "required",
    },
    {
        "key": "admin_account",
        "title": "Admin Account",
        "description": "Create your administrator account",
        "icon": "bi-person-badge",
        "skip_allowed": False,
        "criticality": "required",
    },
    {
        "key": "database",
        "title": "Database Check",
        "description": "Verify database connectivity",
        "icon": "bi-database-check",
        "skip_allowed": False,
        "criticality": "required",
    },
    {
        "key": "communications",
        "title": "Communications",
        "description": "Configure email and SMS providers",
        "icon": "bi-envelope-paper",
        "skip_allowed": True,
        "criticality": "recommended",
        "skip_warning": "Without email or SMS configured, you won't be able to send notifications, OTP codes, or reminders to tenants.",
    },
    {
        "key": "payment",
        "title": "Payment Gateway",
        "description": "Set up payment processing",
        "icon": "bi-credit-card",
        "skip_allowed": True,
        "criticality": "recommended",
        "skip_warning": "Without a payment gateway, tenants cannot pay rent online. You can still record manual payments.",
    },
    {
        "key": "integrations",
        "title": "Integrations",
        "description": "AI, Weather, and Rewards configuration",
        "icon": "bi-puzzle",
        "skip_allowed": True,
        "criticality": "optional",
        "skip_warning": "These integrations enhance the experience but are not required for basic operation.",
    },
    {
        "key": "import",
        "title": "Data Import",
        "description": "Import existing data or load demo data",
        "icon": "bi-cloud-upload",
        "skip_allowed": True,
        "criticality": "optional",
        "skip_warning": "You can always import data later from the admin portal.",
    },
    {
        "key": "review",
        "title": "Review & Complete",
        "description": "Review configuration and finish setup",
        "icon": "bi-check-circle",
        "skip_allowed": False,
        "criticality": "required",
    },
]


def get_wizard_step(key):
    """Get a specific wizard step configuration by key."""
    for step in WIZARD_STEPS:
        if step["key"] == key:
            return step
    return None


def get_step_index(key):
    """Get the index of a step in the wizard."""
    for i, step in enumerate(WIZARD_STEPS):
        if step["key"] == key:
            return i
    return -1


def get_previous_step(key):
    """Get the previous step configuration."""
    idx = get_step_index(key)
    if idx > 0:
        return WIZARD_STEPS[idx - 1]
    return None


def get_next_step(key):
    """Get the next step configuration."""
    idx = get_step_index(key)
    if idx >= 0 and idx < len(WIZARD_STEPS) - 1:
        return WIZARD_STEPS[idx + 1]
    return None
