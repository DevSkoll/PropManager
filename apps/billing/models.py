import secrets
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum

from apps.core.models import AuditMixin, TimeStampedModel


class PaymentGatewayConfig(TimeStampedModel):
    PROVIDER_CHOICES = [
        ("stripe", "Stripe"),
        ("paypal", "PayPal"),
        ("square", "Square"),
    ]

    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    is_active = models.BooleanField(default=False, db_index=True)
    is_default = models.BooleanField(default=False)
    display_name = models.CharField(max_length=100)
    config = models.JSONField(default=dict, help_text="API keys and provider-specific configuration")
    supported_methods = models.JSONField(
        default=list, help_text="List of supported payment methods"
    )

    class Meta:
        ordering = ["-is_default", "provider"]

    def __str__(self):
        default = " (Default)" if self.is_default else ""
        return f"{self.display_name}{default}"

    def save(self, *args, **kwargs):
        if self.is_default:
            PaymentGatewayConfig.objects.filter(is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)


class BillingCycle(TimeStampedModel):
    name = models.CharField(max_length=100)
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="billing_cycles",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.name


class Invoice(TimeStampedModel, AuditMixin):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("issued", "Issued"),
        ("paid", "Paid"),
        ("partial", "Partially Paid"),
        ("overdue", "Overdue"),
        ("cancelled", "Cancelled"),
    ]

    invoice_number = models.CharField(max_length=50, unique=True)
    lease = models.ForeignKey(
        "leases.Lease", on_delete=models.PROTECT, related_name="invoices"
    )
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="invoices"
    )
    billing_cycle = models.ForeignKey(
        BillingCycle, on_delete=models.PROTECT, related_name="invoices", null=True, blank=True
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="draft", db_index=True)
    issue_date = models.DateField()
    due_date = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    late_fees_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-issue_date"]

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.tenant}"

    @property
    def balance_due(self):
        return self.total_amount - self.amount_paid

    def recalculate_total(self):
        """Recompute total_amount from line items."""
        total = self.line_items.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
        self.total_amount = total
        self.save(update_fields=["total_amount"])


class InvoiceLineItem(TimeStampedModel):
    CHARGE_TYPE_CHOICES = [
        ("rent", "Rent"),
        ("water", "Water"),
        ("electric", "Electric"),
        ("gas", "Gas"),
        ("trash", "Trash"),
        ("parking", "Parking"),
        ("pet_fee", "Pet Fee"),
        ("late_fee", "Late Fee"),
        ("other", "Other"),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    charge_type = models.CharField(max_length=15, choices=CHARGE_TYPE_CHOICES)
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    billing_mode = models.CharField(
        max_length=10, blank=True, default="",
        help_text="Billing mode at time of generation: fixed, variable, or empty for non-utility items.",
    )

    def __str__(self):
        return f"{self.description} - ${self.amount}"

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class Payment(TimeStampedModel):
    METHOD_CHOICES = [
        ("online", "Online Payment"),
        ("check", "Check"),
        ("cash", "Cash"),
        ("money_order", "Money Order"),
        ("bank_transfer", "Bank Transfer"),
        ("credit", "Prepayment Credit"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payments"
    )
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=15, choices=METHOD_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="pending", db_index=True)
    reference_number = models.CharField(max_length=100, blank=True, default="")
    gateway_config = models.ForeignKey(
        PaymentGatewayConfig, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments"
    )
    gateway_transaction_id = models.CharField(max_length=255, blank=True, default="")
    credit_applied = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-payment_date"]

    def __str__(self):
        return f"Payment ${self.amount} by {self.tenant} ({self.status})"


class PrepaymentCredit(TimeStampedModel):
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="prepayment_credits"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    remaining_amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255)
    source_payment = models.ForeignKey(
        Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name="credits"
    )

    def __str__(self):
        return f"Credit ${self.remaining_amount} for {self.tenant}"


class UtilityConfig(TimeStampedModel):
    """Per-unit configuration for a single utility type."""

    UTILITY_TYPE_CHOICES = [
        ("water", "Water"),
        ("electric", "Electric"),
        ("gas", "Gas"),
        ("trash", "Trash"),
        ("parking", "Parking"),
        ("pet_fee", "Pet Fee"),
    ]
    BILLING_MODE_CHOICES = [
        ("fixed", "Fixed"),
        ("variable", "Variable"),
        ("included", "Included"),
        ("tenant_pays", "Tenant Pays Separately"),
    ]

    unit = models.ForeignKey(
        "properties.Unit", on_delete=models.CASCADE, related_name="utility_configs"
    )
    utility_type = models.CharField(max_length=15, choices=UTILITY_TYPE_CHOICES)
    billing_mode = models.CharField(max_length=15, choices=BILLING_MODE_CHOICES, default="included")
    rate = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Current monthly rate. Ignored when billing_mode is 'included'.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("unit", "utility_type")]
        ordering = ["unit", "utility_type"]

    def __str__(self):
        return f"{self.unit} - {self.get_utility_type_display()} ({self.get_billing_mode_display()})"


class UtilityRateLog(TimeStampedModel):
    """Audit log entry for rate or billing mode changes on a UtilityConfig."""

    utility_config = models.ForeignKey(
        UtilityConfig, on_delete=models.CASCADE, related_name="rate_logs"
    )
    previous_rate = models.DecimalField(max_digits=10, decimal_places=2)
    new_rate = models.DecimalField(max_digits=10, decimal_places=2)
    previous_billing_mode = models.CharField(max_length=10, blank=True, default="")
    new_billing_mode = models.CharField(max_length=10, blank=True, default="")
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="utility_rate_changes",
    )
    source = models.CharField(
        max_length=20, default="admin_gui",
        help_text="How the change was made: admin_gui, api, bulk_set",
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.utility_config.unit} - {self.utility_config.get_utility_type_display()}: "
            f"${self.previous_rate} → ${self.new_rate}"
        )


class PropertyBillingConfig(TimeStampedModel):
    """Per-property billing defaults (late fees, grace period, auto-generation)."""

    LATE_FEE_TYPE_CHOICES = [
        ("flat", "Flat Amount"),
        ("percentage", "Percentage of Balance"),
    ]
    LATE_FEE_FREQUENCY_CHOICES = [
        ("one_time", "One Time"),
        ("recurring_monthly", "Recurring Monthly"),
    ]

    property = models.OneToOneField(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="billing_config",
    )
    auto_generate_invoices = models.BooleanField(
        default=True,
        help_text="Automatically generate monthly invoices for this property.",
    )
    default_due_day = models.PositiveSmallIntegerField(
        default=1,
        help_text="Day of the month rent is due (1-28).",
    )
    late_fee_enabled = models.BooleanField(default=False)
    grace_period_days = models.PositiveSmallIntegerField(
        default=5,
        help_text="Days after due date before late fee applies.",
    )
    late_fee_type = models.CharField(
        max_length=10, choices=LATE_FEE_TYPE_CHOICES, default="flat",
    )
    late_fee_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Flat dollar amount or percentage (e.g., 5 for 5%).",
    )
    late_fee_frequency = models.CharField(
        max_length=20, choices=LATE_FEE_FREQUENCY_CHOICES, default="one_time",
    )
    late_fee_cap = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Maximum total late fees per invoice. 0 = no cap.",
    )
    interest_enabled = models.BooleanField(default=False)
    annual_interest_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Annual interest rate as percentage (e.g., 12.00 for 12%).",
    )
    default_invoice_notes = models.TextField(
        blank=True, default="",
        help_text="Default notes appended to auto-generated invoices.",
    )

    class Meta:
        verbose_name = "Property Billing Configuration"

    def __str__(self):
        return f"Billing Config: {self.property.name}"

    def clean(self):
        super().clean()
        if self.default_due_day < 1 or self.default_due_day > 28:
            raise ValidationError({"default_due_day": "Due day must be between 1 and 28."})


class RecurringCharge(TimeStampedModel):
    """Charge template that auto-generates InvoiceLineItems on invoices."""

    FREQUENCY_CHOICES = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("annual", "Annual"),
        ("one_time", "One Time"),
    ]

    lease = models.ForeignKey(
        "leases.Lease",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="recurring_charges",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="recurring_charges",
    )
    charge_type = models.CharField(max_length=15, choices=InvoiceLineItem.CHARGE_TYPE_CHOICES)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(
        max_length=10, choices=FREQUENCY_CHOICES, default="monthly",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["charge_type", "description"]

    def __str__(self):
        target = self.lease or self.property
        return f"{self.description} (${self.amount}) -> {target}"

    def clean(self):
        super().clean()
        if not self.lease and not self.property:
            raise ValidationError(
                "A recurring charge must be linked to a lease or a property."
            )
        if self.lease and self.property:
            raise ValidationError(
                "A recurring charge cannot be linked to both a lease and a property."
            )


class LateFeeLog(TimeStampedModel):
    """Audit record of each late fee or interest charge applied to an invoice."""

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="late_fee_logs",
    )
    line_item = models.OneToOneField(
        InvoiceLineItem, on_delete=models.CASCADE, related_name="late_fee_log",
    )
    fee_type = models.CharField(max_length=10)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    applied_date = models.DateField()
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-applied_date"]

    def __str__(self):
        return f"Late fee ${self.amount} on {self.invoice.invoice_number} ({self.applied_date})"


class ApiToken(TimeStampedModel):
    """Simple API token for external system access to billing endpoints."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="api_tokens"
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    label = models.CharField(max_length=100, help_text="Description of what this token is used for.")
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"API Token: {self.label} ({self.user})"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(48)
        super().save(*args, **kwargs)
