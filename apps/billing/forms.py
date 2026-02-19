from django import forms
from django.forms import inlineformset_factory

from .models import (
    BillingCycle,
    Invoice,
    InvoiceLineItem,
    Payment,
    PaymentGatewayConfig,
)


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["lease", "billing_cycle", "issue_date", "due_date", "notes"]
        widgets = {
            "issue_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.leases.models import Lease

        self.fields["lease"].queryset = Lease.objects.filter(status="active").select_related(
            "tenant", "unit"
        )
        self.fields["billing_cycle"].required = False


class InvoiceLineItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceLineItem
        fields = ["charge_type", "description", "quantity", "unit_price"]
        widgets = {
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
        }


InvoiceLineItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceLineItem,
    form=InvoiceLineItemForm,
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class RecordPaymentForm(forms.Form):
    invoice = forms.ModelChoiceField(
        queryset=Invoice.objects.filter(status__in=["issued", "partial", "overdue"]),
        label="Invoice",
    )
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
    )
    method = forms.ChoiceField(choices=Payment.METHOD_CHOICES)
    reference_number = forms.CharField(max_length=100, required=False)
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)


class BatchInvoiceGenerateForm(forms.Form):
    billing_cycle = forms.ModelChoiceField(
        queryset=BillingCycle.objects.filter(is_closed=False),
        label="Billing Cycle",
    )
    confirm = forms.BooleanField(
        label="I confirm I want to generate invoices for all active leases in this billing cycle.",
        required=True,
    )


class PaymentGatewayConfigForm(forms.ModelForm):
    class Meta:
        model = PaymentGatewayConfig
        fields = [
            "provider",
            "display_name",
            "is_active",
            "is_default",
            "config",
            "supported_methods",
        ]
        widgets = {
            "config": forms.Textarea(attrs={"rows": 5, "class": "form-control font-monospace"}),
            "supported_methods": forms.Textarea(
                attrs={"rows": 3, "class": "form-control font-monospace"}
            ),
        }
