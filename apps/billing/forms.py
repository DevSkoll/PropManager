from django import forms

from .models import Invoice, PaymentGatewayConfig


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["lease", "tenant", "issue_date", "due_date", "notes"]
        widgets = {
            "issue_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }


class PaymentGatewayConfigForm(forms.ModelForm):
    class Meta:
        model = PaymentGatewayConfig
        fields = ["provider", "display_name", "is_active", "is_default", "config", "supported_methods"]
