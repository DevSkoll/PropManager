import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import AuditMixin, TimeStampedModel


class Lease(TimeStampedModel, AuditMixin):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("expired", "Expired"),
        ("terminated", "Terminated"),
        ("renewed", "Renewed"),
    ]
    LEASE_TYPE_CHOICES = [
        ("fixed", "Fixed Term"),
        ("month_to_month", "Month to Month"),
    ]
    LATE_FEE_TYPE_CHOICES = [
        ("flat", "Flat Amount"),
        ("percent", "Percentage of Rent"),
        ("daily", "Daily Amount"),
    ]
    SIGNATURE_STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Pending Signatures"),
        ("partial", "Partially Signed"),
        ("executed", "Fully Executed"),
    ]

    # Core lease information
    unit = models.ForeignKey(
        "properties.Unit", on_delete=models.PROTECT, related_name="leases"
    )
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="leases",
        limit_choices_to={"role": "tenant"},
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default="draft", db_index=True
    )
    lease_type = models.CharField(
        max_length=15, choices=LEASE_TYPE_CHOICES, default="fixed"
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    previous_lease = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="renewal"
    )
    notes = models.TextField(blank=True, default="")

    # Rent details
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rent_due_day = models.PositiveSmallIntegerField(
        default=1, help_text="Day of month rent is due (1-28)"
    )
    grace_period_days = models.PositiveSmallIntegerField(
        default=5, help_text="Days after due date before late fee applies"
    )
    late_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    late_fee_type = models.CharField(
        max_length=10, choices=LATE_FEE_TYPE_CHOICES, default="flat"
    )

    # Occupancy
    max_occupants = models.PositiveSmallIntegerField(default=2)
    pets_allowed = models.BooleanField(default=False)
    max_pets = models.PositiveSmallIntegerField(default=0)

    # Policies
    smoking_allowed = models.BooleanField(default=False)
    subletting_allowed = models.BooleanField(default=False)
    renters_insurance_required = models.BooleanField(default=True)
    renters_insurance_minimum = models.DecimalField(
        max_digits=10, decimal_places=2, default=100000,
        help_text="Minimum liability coverage required"
    )

    # Utilities (list of included utilities)
    utilities_included = models.JSONField(
        default=list, blank=True,
        help_text='List of included utilities, e.g. ["water", "trash", "gas"]'
    )

    # Renewal terms
    auto_renewal = models.BooleanField(default=False)
    renewal_notice_days = models.PositiveSmallIntegerField(
        default=30, help_text="Days notice required to not renew"
    )
    rent_increase_notice_days = models.PositiveSmallIntegerField(
        default=60, help_text="Days notice required for rent increases"
    )

    # Parking
    parking_spaces = models.PositiveSmallIntegerField(default=0)
    parking_space_numbers = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Assigned parking space numbers"
    )

    # Move-in/out
    move_in_date = models.DateField(null=True, blank=True)
    move_out_date = models.DateField(null=True, blank=True)
    move_in_inspection_complete = models.BooleanField(default=False)
    move_out_inspection_complete = models.BooleanField(default=False)

    # Signature workflow
    signature_status = models.CharField(
        max_length=15, choices=SIGNATURE_STATUS_CHOICES, default="draft"
    )
    signature_requested_at = models.DateTimeField(null=True, blank=True)
    fully_executed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"Lease: {self.tenant} @ {self.unit} ({self.status})"

    @property
    def is_active(self):
        return self.status == "active"

    @property
    def is_fully_signed(self):
        return self.signature_status == "executed"

    @property
    def occupant_count(self):
        """Returns total occupants including primary tenant."""
        return self.occupants.count() + 1  # +1 for primary tenant

    @property
    def pet_count(self):
        """Returns total pets on this lease."""
        return self.pets.count()

    @property
    def total_monthly_fees(self):
        """Returns sum of all monthly fees."""
        return sum(
            fee.amount for fee in self.fees.filter(frequency="monthly")
        )


class LeaseTerm(TimeStampedModel):
    """Lease terms and conditions."""

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="terms")
    title = models.CharField(max_length=200)
    description = models.TextField()
    is_standard = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.lease} - {self.title}"


class LeaseTermination(TimeStampedModel):
    """Early or scheduled lease termination details."""

    lease = models.OneToOneField(
        Lease, on_delete=models.CASCADE, related_name="termination"
    )
    termination_date = models.DateField()
    reason = models.TextField()
    early_termination_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    fee_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Termination: {self.lease}"


class LeaseOccupant(TimeStampedModel):
    """Additional occupants on the lease (beyond primary tenant)."""

    RELATIONSHIP_CHOICES = [
        ("spouse", "Spouse/Partner"),
        ("child", "Child"),
        ("roommate", "Roommate"),
        ("family", "Family Member"),
        ("cosigner", "Co-Signer"),
        ("other", "Other"),
    ]

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="occupants")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    date_of_birth = models.DateField(null=True, blank=True)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    is_on_lease = models.BooleanField(
        default=True, help_text="Listed on lease vs. just an occupant"
    )
    is_cosigner = models.BooleanField(default=False)
    move_in_date = models.DateField(null=True, blank=True)
    move_out_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_relationship_display()})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class LeasePet(TimeStampedModel):
    """Pets registered on the lease."""

    PET_TYPE_CHOICES = [
        ("dog", "Dog"),
        ("cat", "Cat"),
        ("bird", "Bird"),
        ("fish", "Fish"),
        ("reptile", "Reptile"),
        ("small_animal", "Small Animal"),
        ("other", "Other"),
    ]

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="pets")
    pet_type = models.CharField(max_length=20, choices=PET_TYPE_CHOICES)
    name = models.CharField(max_length=100)
    breed = models.CharField(max_length=100, blank=True, default="")
    weight_lbs = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True
    )
    color = models.CharField(max_length=50, blank=True, default="")
    is_service_animal = models.BooleanField(default=False)
    vaccination_current = models.BooleanField(default=False)
    pet_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monthly_pet_rent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_pet_type_display()})"


class LeaseFee(TimeStampedModel):
    """Fees associated with the lease."""

    FEE_TYPE_CHOICES = [
        ("application", "Application Fee"),
        ("admin", "Administrative Fee"),
        ("pet_deposit", "Pet Deposit"),
        ("pet_rent", "Monthly Pet Rent"),
        ("parking", "Parking Fee"),
        ("storage", "Storage Fee"),
        ("late", "Late Payment Fee"),
        ("nsf", "NSF/Returned Check Fee"),
        ("move_in", "Move-In Fee"),
        ("move_out", "Move-Out Fee"),
        ("cleaning", "Cleaning Fee"),
        ("key_replacement", "Key Replacement"),
        ("lock_change", "Lock Change Fee"),
        ("amenity", "Amenity Fee"),
        ("utility", "Utility Fee"),
        ("other", "Other"),
    ]
    FREQUENCY_CHOICES = [
        ("one_time", "One-Time"),
        ("monthly", "Monthly"),
        ("annual", "Annual"),
        ("per_occurrence", "Per Occurrence"),
    ]

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="fees")
    fee_type = models.CharField(max_length=20, choices=FEE_TYPE_CHOICES)
    name = models.CharField(max_length=100, help_text="Custom name for this fee")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    is_refundable = models.BooleanField(default=False)
    description = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["fee_type", "name"]

    def __str__(self):
        return f"{self.name}: ${self.amount} ({self.get_frequency_display()})"


class LeaseSignature(TimeStampedModel):
    """Electronic signature capture for lease agreements."""

    SIGNER_TYPE_CHOICES = [
        ("tenant", "Tenant"),
        ("occupant", "Occupant"),
        ("cosigner", "Co-Signer"),
        ("landlord", "Landlord/Manager"),
    ]

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="signatures")
    signer_type = models.CharField(max_length=20, choices=SIGNER_TYPE_CHOICES)
    signer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lease_signatures",
    )
    signer_name = models.CharField(max_length=200, help_text="Typed name confirmation")
    signer_email = models.EmailField()

    # Signature data
    signature_image = models.TextField(
        blank=True, default="", help_text="Base64 encoded signature image"
    )
    signed_at = models.DateTimeField(null=True, blank=True)

    # Audit trail
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")

    # Token for external signers (occupants/cosigners without accounts)
    signing_token = models.CharField(max_length=64, unique=True, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("lease", "signer_email")]
        ordering = ["signer_type", "signer_name"]

    def __str__(self):
        status = "Signed" if self.signed_at else "Pending"
        return f"{self.signer_name} ({self.get_signer_type_display()}) - {status}"

    def save(self, *args, **kwargs):
        if not self.signing_token:
            self.signing_token = secrets.token_urlsafe(48)
        super().save(*args, **kwargs)

    @property
    def is_signed(self):
        return self.signed_at is not None

    @property
    def is_token_valid(self):
        if not self.token_expires_at:
            return False
        return timezone.now() < self.token_expires_at

    def generate_new_token(self, expires_in_days=7):
        """Generate a new signing token with expiration."""
        self.signing_token = secrets.token_urlsafe(48)
        self.token_expires_at = timezone.now() + timezone.timedelta(days=expires_in_days)
        self.save(update_fields=["signing_token", "token_expires_at"])
