from decimal import Decimal

from django import forms
from django.forms import inlineformset_factory

from .models import (
    BillingCycle,
    Invoice,
    InvoiceLineItem,
    Payment,
    PaymentGatewayConfig,
    PropertyBillingConfig,
    RecurringCharge,
    UtilityConfig,
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

InvoiceEditLineItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceLineItem,
    form=InvoiceLineItemForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
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
    method = forms.ChoiceField(
        choices=[c for c in Payment.METHOD_CHOICES if c[0] not in ("online", "credit")],
    )
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


class UtilityConfigForm(forms.ModelForm):
    class Meta:
        model = UtilityConfig
        fields = ["utility_type", "billing_mode", "rate", "is_active"]
        widgets = {
            "utility_type": forms.Select(attrs={"class": "form-select", "readonly": "readonly"}),
            "billing_mode": forms.Select(attrs={"class": "form-select"}),
            "rate": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get("billing_mode")
        rate = cleaned.get("rate")
        if mode in ("fixed", "variable") and (rate is None or rate <= 0):
            self.add_error("rate", "Rate must be greater than zero for fixed/variable billing.")
        if mode in ("included", "tenant_pays"):
            cleaned["rate"] = Decimal("0.00")
        return cleaned


def get_utility_config_formset():
    from apps.properties.models import Unit
    return inlineformset_factory(
        Unit,
        UtilityConfig,
        form=UtilityConfigForm,
        extra=0,
        can_delete=False,
        min_num=0,
        validate_min=False,
    )


class BulkUtilityConfigForm(forms.Form):
    property = forms.ModelChoiceField(
        queryset=None,
        label="Property",
    )
    utility_type = forms.ChoiceField(choices=UtilityConfig.UTILITY_TYPE_CHOICES)
    billing_mode = forms.ChoiceField(choices=UtilityConfig.BILLING_MODE_CHOICES)
    rate = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
    )
    confirm = forms.BooleanField(
        label="I confirm I want to apply this to all units in the selected property.",
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.properties.models import Property
        self.fields["property"].queryset = Property.objects.filter(is_active=True)

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get("billing_mode")
        rate = cleaned.get("rate")
        if mode in ("fixed", "variable") and (rate is None or rate <= 0):
            self.add_error("rate", "Rate is required for fixed/variable billing.")
        if mode in ("included", "tenant_pays"):
            cleaned["rate"] = Decimal("0.00")
        return cleaned


# ---------------------------------------------------------------------------
# New forms for billing overhaul
# ---------------------------------------------------------------------------


class PropertyBillingConfigForm(forms.ModelForm):
    class Meta:
        model = PropertyBillingConfig
        exclude = ["property"]
        widgets = {
            "default_due_day": forms.NumberInput(attrs={"min": 1, "max": 28}),
            "grace_period_days": forms.NumberInput(attrs={"min": 0, "max": 60}),
            "late_fee_amount": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "late_fee_cap": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "annual_interest_rate": forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "100"}),
            "default_invoice_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_default_due_day(self):
        day = self.cleaned_data["default_due_day"]
        if day < 1 or day > 28:
            raise forms.ValidationError("Due day must be between 1 and 28.")
        return day


class RecurringChargeForm(forms.ModelForm):
    class Meta:
        model = RecurringCharge
        fields = [
            "charge_type",
            "description",
            "amount",
            "frequency",
            "is_active",
            "start_date",
            "end_date",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }


class TenantPaymentForm(forms.Form):
    """Form for tenant-initiated payments."""

    apply_credits = forms.BooleanField(
        required=False,
        initial=True,
        label="Apply available prepayment credits",
    )


# ---------------------------------------------------------------------------
# Provider-specific gateway configuration forms
# ---------------------------------------------------------------------------


class GatewayBaseForm(forms.ModelForm):
    class Meta:
        model = PaymentGatewayConfig
        fields = ["display_name", "is_active", "is_default"]


class ProviderConfigForm(forms.Form):
    """Base class for provider-specific config forms.

    Serializes fields to/from the config JSONField.
    """

    def __init__(self, *args, config_data=None, **kwargs):
        super().__init__(*args, **kwargs)
        if config_data:
            for field_name, field in self.fields.items():
                if field_name in config_data:
                    self.fields[field_name].initial = config_data[field_name]

    def get_config_data(self):
        """Return cleaned data as a dict for the config JSONField."""
        return {k: v for k, v in self.cleaned_data.items() if v not in (None, "")}


class StripeConfigForm(ProviderConfigForm):
    secret_key = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text="From Stripe Dashboard \u2192 Developers \u2192 API Keys",
    )
    publishable_key = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text="Starts with pk_test_ or pk_live_",
    )
    webhook_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text="From Stripe Dashboard \u2192 Developers \u2192 Webhooks",
    )


class PayPalConfigForm(ProviderConfigForm):
    client_id = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text="From PayPal Developer Dashboard \u2192 My Apps & Credentials",
    )
    client_secret = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    mode = forms.ChoiceField(
        choices=[("sandbox", "Sandbox"), ("live", "Live")],
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    webhook_id = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text="From PayPal Developer Dashboard \u2192 Webhooks",
    )


class SquareConfigForm(ProviderConfigForm):
    access_token = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text="From Square Developer Dashboard \u2192 Credentials",
    )
    application_id = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text="From Square Developer Dashboard \u2192 Credentials",
    )
    location_id = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text="From Square Dashboard \u2192 Locations",
    )
    environment = forms.ChoiceField(
        choices=[("sandbox", "Sandbox"), ("production", "Production")],
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    webhook_signature_key = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    webhook_url = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text="Your webhook endpoint URL",
    )


class AuthorizeNetConfigForm(ProviderConfigForm):
    api_login_id = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text="From Merchant Interface \u2192 Account \u2192 Security Settings",
    )
    transaction_key = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    signature_key = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text="For webhook verification",
    )
    client_key = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text="Public key for Accept.js",
    )
    environment = forms.ChoiceField(
        choices=[("sandbox", "Sandbox"), ("production", "Production")],
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class BraintreeConfigForm(ProviderConfigForm):
    merchant_id = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text="From Braintree Control Panel \u2192 Settings \u2192 API",
    )
    public_key = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    private_key = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    environment = forms.ChoiceField(
        choices=[("sandbox", "Sandbox"), ("production", "Production")],
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class PlaidAchConfigForm(ProviderConfigForm):
    plaid_client_id = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text="From Plaid Dashboard \u2192 Team Settings \u2192 Keys",
    )
    plaid_secret = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    plaid_environment = forms.ChoiceField(
        choices=[
            ("sandbox", "Sandbox"),
            ("development", "Development"),
            ("production", "Production"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    stripe_secret_key = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text="Stripe key for ACH processing",
    )
    stripe_publishable_key = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class BitcoinConfigForm(ProviderConfigForm):
    xpub = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        help_text="Extended public key (xpub/zpub) for address derivation",
    )
    network = forms.ChoiceField(
        choices=[("bitcoin", "Mainnet"), ("testnet", "Testnet")],
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    payment_window_minutes = forms.IntegerField(
        initial=60,
        min_value=15,
        max_value=1440,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        help_text="Minutes before a BTC payment expires",
    )
    required_confirmations = forms.IntegerField(
        initial=1,
        min_value=0,
        max_value=6,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    hot_wallet_encrypted_key = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text="Optional: Encrypted private key for automated sweeps",
    )


PROVIDER_FORM_MAP = {
    "stripe": StripeConfigForm,
    "paypal": PayPalConfigForm,
    "square": SquareConfigForm,
    "authorize_net": AuthorizeNetConfigForm,
    "braintree": BraintreeConfigForm,
    "plaid_ach": PlaidAchConfigForm,
    "bitcoin": BitcoinConfigForm,
}
