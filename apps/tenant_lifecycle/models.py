"""
Tenant Lifecycle Models.

Models for managing the complete tenant onboarding process including:
- Onboarding templates (property-level configuration)
- Onboarding sessions (individual tenant journeys)
- Data collection models (vehicles, employment, insurance, ID verification)
- Payment and document tracking
"""

import secrets
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_access_token():
    """Generate a secure 48-character access token."""
    return secrets.token_urlsafe(36)


class TimeStampedModel(models.Model):
    """Abstract base model with created/updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# =============================================================================
# Onboarding Preset (Reusable Template Configurations)
# =============================================================================


class OnboardingPreset(TimeStampedModel):
    """
    Reusable onboarding template configurations.

    Presets are not tied to any property and can be used as starting points
    when creating OnboardingTemplates for specific properties.
    """

    PRESET_CATEGORY_CHOICES = [
        ("residential", "Residential"),
        ("student", "Student Housing"),
        ("senior", "Senior Living"),
        ("commercial", "Commercial"),
        ("subsidized", "Subsidized/Section 8"),
        ("custom", "Custom"),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(
        blank=True,
        help_text="Description of when to use this preset.",
    )
    category = models.CharField(
        max_length=20,
        choices=PRESET_CATEGORY_CHOICES,
        default="residential",
    )
    icon = models.CharField(
        max_length=50,
        default="bi-house",
        help_text="Bootstrap icon class for display.",
    )

    # Whether this is a system preset (cannot be deleted)
    is_system = models.BooleanField(
        default=False,
        help_text="System presets cannot be deleted.",
    )
    is_active = models.BooleanField(default=True)

    # Step configuration (same structure as OnboardingTemplate)
    steps_config = models.JSONField(
        default=dict,
        help_text="Configuration for each onboarding step.",
    )

    # Data collection flags
    collect_vehicles = models.BooleanField(default=True)
    collect_employment = models.BooleanField(default=True)
    require_renters_insurance = models.BooleanField(default=False)
    require_id_verification = models.BooleanField(default=False)

    # Default welcome content
    welcome_message = models.TextField(blank=True)
    property_rules = models.TextField(blank=True)
    move_in_checklist = models.JSONField(default=list)

    # Default invitation messaging
    invitation_email_subject = models.CharField(
        max_length=200,
        default="Welcome! Complete Your Move-In Process",
    )
    invitation_email_body = models.TextField(blank=True)
    invitation_sms_body = models.CharField(max_length=320, blank=True)

    # Link settings
    link_expiry_days = models.PositiveSmallIntegerField(default=14)

    # Default fees (stored as JSON for flexibility)
    default_fees = models.JSONField(
        default=list,
        help_text="List of default fee configurations.",
    )

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    def apply_to_template(self, template):
        """
        Apply this preset's configuration to an OnboardingTemplate.

        Args:
            template: OnboardingTemplate instance to configure

        Returns:
            The configured template (unsaved)
        """
        template.steps_config = self.steps_config.copy()
        template.collect_vehicles = self.collect_vehicles
        template.collect_employment = self.collect_employment
        template.require_renters_insurance = self.require_renters_insurance
        template.require_id_verification = self.require_id_verification
        template.welcome_message = self.welcome_message
        template.property_rules = self.property_rules
        template.move_in_checklist = self.move_in_checklist.copy()
        template.invitation_email_subject = self.invitation_email_subject
        template.invitation_email_body = self.invitation_email_body
        template.invitation_sms_body = self.invitation_sms_body
        template.link_expiry_days = self.link_expiry_days
        return template

    def create_template_for_property(self, prop, name=None, is_default=False):
        """
        Create a new OnboardingTemplate for a property using this preset.

        Args:
            prop: Property instance
            name: Optional custom name (defaults to preset name)
            is_default: Whether this should be the default template

        Returns:
            Saved OnboardingTemplate instance
        """
        template = OnboardingTemplate(
            name=name or self.name,
            property=prop,
            is_default=is_default,
        )
        self.apply_to_template(template)
        template.save()

        # Create default fees from preset
        for idx, fee_config in enumerate(self.default_fees):
            OnboardingTemplateFee.objects.create(
                template=template,
                fee_type=fee_config.get("fee_type", "other"),
                name=fee_config.get("name", "Fee"),
                description=fee_config.get("description", ""),
                amount=fee_config.get("amount"),
                use_lease_value=fee_config.get("use_lease_value", False),
                lease_field=fee_config.get("lease_field", ""),
                is_required=fee_config.get("is_required", True),
                is_refundable=fee_config.get("is_refundable", False),
                order=idx,
            )

        return template


# =============================================================================
# Onboarding Template Models
# =============================================================================


class OnboardingTemplate(TimeStampedModel):
    """
    Property-level configuration for the onboarding process.

    Defines which steps are enabled, required documents, fees, and messaging.
    Each property can have multiple templates (e.g., standard, pet-friendly).
    """

    name = models.CharField(max_length=100)
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="onboarding_templates",
    )

    # Status
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(
        default=False,
        help_text="If true, this is the default template for this property.",
    )

    # Step configuration (JSON object with step settings)
    steps_config = models.JSONField(
        default=dict,
        help_text="Configuration for each onboarding step (enabled, order, required).",
    )

    # Data collection flags (convenience fields for common toggles)
    collect_vehicles = models.BooleanField(default=True)
    collect_employment = models.BooleanField(default=True)
    require_renters_insurance = models.BooleanField(default=False)
    require_id_verification = models.BooleanField(default=False)

    # Welcome content
    welcome_message = models.TextField(
        blank=True,
        help_text="Welcome message displayed at the end of onboarding.",
    )
    property_rules = models.TextField(
        blank=True,
        help_text="Property rules and guidelines shown to tenant.",
    )
    move_in_checklist = models.JSONField(
        default=list,
        help_text="List of move-in checklist items for the tenant.",
    )

    # Invitation messaging
    invitation_email_subject = models.CharField(
        max_length=200,
        default="Welcome! Complete Your Move-In Process",
    )
    invitation_email_body = models.TextField(
        blank=True,
        help_text="Custom email body for invitation. Use {{link}} for the onboarding URL.",
    )
    invitation_sms_body = models.CharField(
        max_length=320,
        blank=True,
        help_text="SMS message for invitation. Use {{link}} for the URL.",
    )

    # Link settings
    link_expiry_days = models.PositiveSmallIntegerField(
        default=14,
        help_text="Number of days before onboarding link expires.",
    )

    class Meta:
        ordering = ["property", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["property"],
                condition=models.Q(is_default=True),
                name="unique_default_template_per_property",
            ),
        ]

    def __str__(self):
        return f"{self.property.name} - {self.name}"

    def save(self, *args, **kwargs):
        # If this is being set as default, unset other defaults for this property
        if self.is_default:
            OnboardingTemplate.objects.filter(
                property=self.property, is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def get_enabled_steps(self):
        """Return list of enabled steps in order."""
        steps = []
        for step_name, config in self.steps_config.items():
            if config.get("enabled", True):
                steps.append({
                    "name": step_name,
                    "order": config.get("order", 99),
                    "required": config.get("required", False),
                })
        return sorted(steps, key=lambda x: x["order"])

    @classmethod
    def get_default_steps_config(cls):
        """Return the default steps configuration."""
        return {
            "account_creation": {"enabled": True, "order": 1, "required": True},
            "personal_info": {"enabled": True, "order": 2, "required": True},
            "emergency_contacts": {"enabled": True, "order": 3, "required": True},
            "occupants": {"enabled": True, "order": 4, "required": False},
            "pets": {"enabled": True, "order": 5, "required": False},
            "vehicles": {"enabled": True, "order": 6, "required": False},
            "employment": {"enabled": True, "order": 7, "required": False},
            "insurance": {"enabled": True, "order": 8, "required": False},
            "id_verification": {"enabled": False, "order": 9, "required": False},
            "documents": {"enabled": True, "order": 10, "required": True},
            "payments": {"enabled": True, "order": 11, "required": True},
            "move_in_schedule": {"enabled": True, "order": 12, "required": False},
            "welcome": {"enabled": True, "order": 13, "required": True},
        }


class OnboardingTemplateDocument(TimeStampedModel):
    """
    Documents required for an onboarding template.

    Links to EDocumentTemplate for automatic document generation.
    """

    template = models.ForeignKey(
        OnboardingTemplate,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    edocument_template = models.ForeignKey(
        "documents.EDocumentTemplate",
        on_delete=models.CASCADE,
        related_name="onboarding_usages",
    )
    order = models.PositiveSmallIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional description shown to tenant.",
    )

    class Meta:
        ordering = ["order"]
        unique_together = ["template", "edocument_template"]

    def __str__(self):
        return f"{self.template.name} - {self.edocument_template.name}"


class OnboardingTemplateFee(TimeStampedModel):
    """
    Fees required for an onboarding template.

    Can specify a fixed amount or reference a lease field (e.g., security_deposit).
    """

    FEE_TYPE_CHOICES = [
        ("security_deposit", "Security Deposit"),
        ("first_month", "First Month's Rent"),
        ("last_month", "Last Month's Rent"),
        ("pet_deposit", "Pet Deposit"),
        ("pet_fee", "Pet Fee (Non-Refundable)"),
        ("admin_fee", "Administrative Fee"),
        ("application_fee", "Application Fee"),
        ("key_deposit", "Key Deposit"),
        ("parking_fee", "Parking Fee"),
        ("other", "Other Fee"),
    ]

    template = models.ForeignKey(
        OnboardingTemplate,
        on_delete=models.CASCADE,
        related_name="fees",
    )
    fee_type = models.CharField(max_length=20, choices=FEE_TYPE_CHOICES)
    name = models.CharField(
        max_length=100,
        help_text="Display name for this fee.",
    )
    description = models.CharField(max_length=255, blank=True)

    # Amount configuration
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Fixed amount. Leave blank to use lease value.",
    )
    use_lease_value = models.BooleanField(
        default=False,
        help_text="If true, pull amount from lease field.",
    )
    lease_field = models.CharField(
        max_length=50,
        blank=True,
        help_text="Lease field to pull value from (e.g., 'monthly_rent', 'security_deposit').",
    )

    is_required = models.BooleanField(default=True)
    is_refundable = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.template.name} - {self.name}"

    def get_amount_for_lease(self, lease):
        """Calculate the fee amount for a specific lease."""
        if self.use_lease_value and self.lease_field and lease:
            value = getattr(lease, self.lease_field, None)
            if value is not None:
                return Decimal(str(value))
        return self.amount or Decimal("0.00")


# =============================================================================
# Onboarding Session Models
# =============================================================================


class OnboardingSession(TimeStampedModel):
    """
    Individual tenant onboarding session.

    Tracks the progress of a single tenant through the onboarding process.
    """

    STATUS_CHOICES = [
        ("invited", "Invited"),
        ("started", "Started"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
    ]

    template = models.ForeignKey(
        OnboardingTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sessions",
    )
    unit = models.ForeignKey(
        "properties.Unit",
        on_delete=models.CASCADE,
        related_name="onboarding_sessions",
    )
    lease = models.ForeignKey(
        "leases.Lease",
        on_delete=models.SET_NULL,
        null=True,
        blank=False,
        related_name="onboarding_sessions",
        help_text="Lease for this onboarding (required).",
    )
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_sessions",
        help_text="Created user account (populated during account creation step).",
    )

    # Prospective tenant info (before account creation)
    prospective_email = models.EmailField()
    prospective_phone = models.CharField(max_length=20, blank=True)
    prospective_first_name = models.CharField(max_length=50)
    prospective_last_name = models.CharField(max_length=50)

    # Session state
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="invited",
    )
    current_step = models.CharField(
        max_length=50,
        default="account_creation",
    )
    steps_completed = models.JSONField(
        default=dict,
        help_text="Dict mapping step names to completion timestamps.",
    )

    # Access token
    access_token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_access_token,
    )
    token_expires_at = models.DateTimeField()

    # Email verification OTP
    otp_code = models.CharField(max_length=6, blank=True, default="")
    otp_expires_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    invitation_sent_at = models.DateTimeField(null=True, blank=True)
    first_accessed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Collected personal data
    collected_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Personal info collected during onboarding (DOB, ID info).",
    )

    # Admin notes
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about this session.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_onboarding_sessions",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Onboarding: {self.prospective_first_name} {self.prospective_last_name} - {self.unit}"

    def save(self, *args, **kwargs):
        # Set default expiry if not set
        if not self.token_expires_at:
            days = self.template.link_expiry_days if self.template else 14
            self.token_expires_at = timezone.now() + timezone.timedelta(days=days)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Check if the session token has expired."""
        return timezone.now() > self.token_expires_at

    @property
    def is_active(self):
        """Check if session is still active (not completed, cancelled, or expired)."""
        if self.status in ("completed", "cancelled", "expired"):
            return False
        return not self.is_expired

    @property
    def prospective_full_name(self):
        return f"{self.prospective_first_name} {self.prospective_last_name}"

    def get_next_step(self):
        """Determine the next incomplete step based on template config."""
        if not self.template:
            return None

        enabled_steps = self.template.get_enabled_steps()
        for step in enabled_steps:
            step_name = step["name"]
            if step_name not in self.steps_completed:
                return step_name
        return None

    def mark_step_complete(self, step_name):
        """Mark a step as completed."""
        self.steps_completed[step_name] = timezone.now().isoformat()
        self.current_step = self.get_next_step() or "complete"
        if self.status == "invited":
            self.status = "in_progress"
        self.save(update_fields=["steps_completed", "current_step", "status", "updated_at"])

    def regenerate_token(self, expiry_days=None):
        """Generate a new access token and extend expiry."""
        self.access_token = generate_access_token()
        days = expiry_days or (self.template.link_expiry_days if self.template else 14)
        self.token_expires_at = timezone.now() + timezone.timedelta(days=days)
        self.status = "invited"
        self.save(update_fields=["access_token", "token_expires_at", "status", "updated_at"])

    def generate_otp(self):
        """Generate OTP code for email verification."""
        from django.conf import settings as django_settings

        if django_settings.DEBUG:
            # Use static code in development
            self.otp_code = "123456"
        else:
            import random
            self.otp_code = "".join([str(random.randint(0, 9)) for _ in range(6)])

        self.otp_expires_at = timezone.now() + timezone.timedelta(minutes=10)
        self.save(update_fields=["otp_code", "otp_expires_at", "updated_at"])
        return self.otp_code

    def verify_otp(self, code):
        """Verify OTP code. Returns True if valid."""
        if not self.otp_code or not self.otp_expires_at:
            return False
        if timezone.now() > self.otp_expires_at:
            return False
        return self.otp_code == code

    def get_progress_percent(self):
        """Calculate completion percentage."""
        if not self.template:
            return 0
        enabled_steps = self.template.get_enabled_steps()
        if not enabled_steps:
            return 100
        completed_count = sum(
            1 for step in enabled_steps if step["name"] in self.steps_completed
        )
        return int((completed_count / len(enabled_steps)) * 100)


class OnboardingStepLog(TimeStampedModel):
    """
    Audit trail for onboarding step attempts.

    Logs each attempt at a step with timestamps and metadata.
    """

    session = models.ForeignKey(
        OnboardingSession,
        on_delete=models.CASCADE,
        related_name="step_logs",
    )
    step_name = models.CharField(max_length=50)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    attempt_number = models.PositiveSmallIntegerField(default=1)

    # Client info
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Data snapshot (for debugging/audit)
    data_snapshot = models.JSONField(
        default=dict,
        help_text="Snapshot of submitted data for this step.",
    )

    class Meta:
        ordering = ["session", "started_at"]

    def __str__(self):
        return f"{self.session} - {self.step_name} (Attempt {self.attempt_number})"


# =============================================================================
# Tenant Data Collection Models
# =============================================================================


class TenantEmergencyContact(TimeStampedModel):
    """
    Emergency contact information for tenants.

    Used during onboarding and for ongoing contact management.
    """

    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergency_contacts",
    )
    lease = models.ForeignKey(
        "leases.Lease",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_contacts",
    )
    onboarding_session = models.ForeignKey(
        OnboardingSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_contacts",
    )

    # Contact details
    name = models.CharField(max_length=150)
    relationship = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    # Metadata
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "name"]

    def __str__(self):
        return f"{self.name} ({self.relationship})"


class TenantVehicle(TimeStampedModel):
    """
    Vehicle registration for tenants.

    Supports both onboarding collection and ongoing management.
    """

    VEHICLE_TYPE_CHOICES = [
        ("car", "Car"),
        ("truck", "Truck"),
        ("suv", "SUV"),
        ("van", "Van"),
        ("motorcycle", "Motorcycle"),
        ("rv", "RV/Motorhome"),
        ("trailer", "Trailer"),
        ("other", "Other"),
    ]

    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vehicles",
    )
    lease = models.ForeignKey(
        "leases.Lease",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicles",
    )
    onboarding_session = models.ForeignKey(
        OnboardingSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicles",
    )

    # Vehicle details
    vehicle_type = models.CharField(
        max_length=20,
        choices=VEHICLE_TYPE_CHOICES,
        default="car",
    )
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    color = models.CharField(max_length=30)
    license_plate = models.CharField(max_length=20)
    state = models.CharField(max_length=2, help_text="State/province code.")

    # Parking info
    parking_space = models.CharField(max_length=20, blank=True)
    parking_permit_number = models.CharField(max_length=50, blank=True)

    # Status
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-is_primary", "make", "model"]

    def __str__(self):
        return f"{self.year or ''} {self.make} {self.model} ({self.license_plate})"


class TenantEmployment(TimeStampedModel):
    """
    Employment and income information for tenants.

    Used for income verification during onboarding.
    """

    EMPLOYMENT_TYPE_CHOICES = [
        ("full_time", "Full-Time Employee"),
        ("part_time", "Part-Time Employee"),
        ("self_employed", "Self-Employed"),
        ("contractor", "Independent Contractor"),
        ("retired", "Retired"),
        ("student", "Student"),
        ("unemployed", "Currently Unemployed"),
        ("other", "Other"),
    ]

    INCOME_FREQUENCY_CHOICES = [
        ("weekly", "Weekly"),
        ("biweekly", "Bi-Weekly"),
        ("semimonthly", "Semi-Monthly"),
        ("monthly", "Monthly"),
        ("annual", "Annually"),
    ]

    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employment_records",
    )
    lease = models.ForeignKey(
        "leases.Lease",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employment_records",
    )
    onboarding_session = models.ForeignKey(
        OnboardingSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employment_records",
    )

    # Employment details
    employment_type = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_TYPE_CHOICES,
    )
    employer_name = models.CharField(max_length=100, blank=True)
    employer_phone = models.CharField(max_length=20, blank=True)
    employer_address = models.TextField(blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    start_date = models.DateField(null=True, blank=True)

    # Income
    gross_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    income_frequency = models.CharField(
        max_length=20,
        choices=INCOME_FREQUENCY_CHOICES,
        default="monthly",
    )
    additional_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    additional_income_source = models.CharField(max_length=100, blank=True)

    # Status
    is_current = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_employments",
    )

    class Meta:
        ordering = ["-is_current", "-start_date"]

    def __str__(self):
        if self.employer_name:
            return f"{self.tenant} - {self.employer_name}"
        return f"{self.tenant} - {self.get_employment_type_display()}"

    @property
    def monthly_income(self):
        """Calculate monthly income from gross income and frequency."""
        if not self.gross_income:
            return Decimal("0.00")

        multipliers = {
            "weekly": Decimal("4.33"),
            "biweekly": Decimal("2.17"),
            "semimonthly": Decimal("2"),
            "monthly": Decimal("1"),
            "annual": Decimal("0.0833"),
        }
        multiplier = multipliers.get(self.income_frequency, Decimal("1"))
        return self.gross_income * multiplier


class TenantInsurance(TimeStampedModel):
    """
    Renter's insurance policy tracking.
    """

    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="insurance_policies",
    )
    lease = models.ForeignKey(
        "leases.Lease",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="insurance_policies",
    )
    onboarding_session = models.ForeignKey(
        OnboardingSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="insurance_records",
    )

    # Policy details
    provider_name = models.CharField(max_length=100)
    policy_number = models.CharField(max_length=50)
    coverage_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Personal property coverage amount.",
    )
    liability_coverage = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Liability coverage amount.",
    )
    start_date = models.DateField()
    end_date = models.DateField()

    # Document
    policy_document = models.FileField(
        upload_to="tenant_insurance/%Y/%m/",
        blank=True,
    )

    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_insurance_policies",
    )

    class Meta:
        ordering = ["-start_date"]
        verbose_name_plural = "Tenant insurance policies"

    def __str__(self):
        return f"{self.tenant} - {self.provider_name} ({self.policy_number})"

    @property
    def is_expired(self):
        return self.end_date < timezone.now().date()


class TenantIDVerification(TimeStampedModel):
    """
    ID verification document storage.
    """

    ID_TYPE_CHOICES = [
        ("drivers_license", "Driver's License"),
        ("state_id", "State ID"),
        ("passport", "Passport"),
        ("military_id", "Military ID"),
        ("other", "Other Government ID"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="id_verifications",
    )
    lease = models.ForeignKey(
        "leases.Lease",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="id_verifications",
    )
    onboarding_session = models.ForeignKey(
        OnboardingSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="id_verifications",
    )

    # ID details
    id_type = models.CharField(max_length=20, choices=ID_TYPE_CHOICES)
    id_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Last 4 digits only for security.",
    )
    issuing_state = models.CharField(max_length=50, blank=True)
    expiration_date = models.DateField(null=True, blank=True)

    # Documents (front and back)
    front_image = models.ImageField(upload_to="id_verification/%Y/%m/")
    back_image = models.ImageField(
        upload_to="id_verification/%Y/%m/",
        blank=True,
    )

    # Verification status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    rejection_reason = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_id_verifications",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tenant} - {self.get_id_type_display()}"


# =============================================================================
# Onboarding Payment & Document Tracking
# =============================================================================


class OnboardingPayment(TimeStampedModel):
    """
    Payment tracking for onboarding session.

    Links to Invoice/Payment models once payment is processed.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    session = models.ForeignKey(
        OnboardingSession,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    template_fee = models.ForeignKey(
        OnboardingTemplateFee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )

    # Fee details (denormalized for historical accuracy)
    fee_type = models.CharField(max_length=20)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_refundable = models.BooleanField(default=False)

    # Payment status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    # Links to billing system
    invoice = models.ForeignKey(
        "billing.Invoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_payments",
    )
    payment = models.ForeignKey(
        "billing.Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_payments",
    )

    # Payment attempt tracking
    last_error = models.TextField(blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["session", "template_fee__order"]

    def __str__(self):
        return f"{self.session} - {self.description} (${self.amount})"


class OnboardingDocument(TimeStampedModel):
    """
    Document tracking for onboarding session.

    Links to EDocument for signing workflow.
    """

    session = models.ForeignKey(
        OnboardingSession,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    template_document = models.ForeignKey(
        OnboardingTemplateDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="instances",
    )
    edocument = models.ForeignKey(
        "documents.EDocument",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_records",
    )

    is_required = models.BooleanField(default=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["template_document__order"]

    def __str__(self):
        doc_name = self.edocument.title if self.edocument else "Pending"
        return f"{self.session} - {doc_name}"

    @property
    def is_signed(self):
        return self.signed_at is not None
