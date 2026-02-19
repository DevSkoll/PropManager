from django.conf import settings
from django.db import models

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
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-issue_date"]

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.tenant}"

    @property
    def balance_due(self):
        return self.total_amount - self.amount_paid


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
