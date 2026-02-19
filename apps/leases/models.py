from django.conf import settings
from django.db import models

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

    unit = models.ForeignKey("properties.Unit", on_delete=models.PROTECT, related_name="leases")
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="leases",
        limit_choices_to={"role": "tenant"},
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="draft", db_index=True)
    lease_type = models.CharField(max_length=15, choices=LEASE_TYPE_CHOICES, default="fixed")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    previous_lease = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="renewal"
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"Lease: {self.tenant} @ {self.unit} ({self.status})"

    @property
    def is_active(self):
        return self.status == "active"


class LeaseTerm(TimeStampedModel):
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="terms")
    title = models.CharField(max_length=200)
    description = models.TextField()
    is_standard = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.lease} - {self.title}"


class LeaseTermination(TimeStampedModel):
    lease = models.OneToOneField(Lease, on_delete=models.CASCADE, related_name="termination")
    termination_date = models.DateField()
    reason = models.TextField()
    early_termination_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fee_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Termination: {self.lease}"
