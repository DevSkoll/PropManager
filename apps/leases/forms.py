from django import forms

from .models import Lease, LeaseFee, LeaseOccupant, LeasePet, LeaseSignature, LeaseTerm


class LeaseForm(forms.ModelForm):
    TENANT_MODE_CHOICES = [
        ("existing", "Select Existing Tenant"),
        ("new", "New Tenant (Onboarding Required)"),
    ]

    tenant_mode = forms.ChoiceField(
        choices=TENANT_MODE_CHOICES,
        initial="existing",
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        label="Tenant Selection",
    )

    class Meta:
        model = Lease
        fields = [
            # Core
            "unit", "tenant", "status", "lease_type", "start_date", "end_date",
            # Prospective tenant (for new tenant mode)
            "prospective_first_name", "prospective_last_name",
            "prospective_email", "prospective_phone",
            # Rent
            "monthly_rent", "security_deposit", "rent_due_day", "grace_period_days",
            "late_fee_amount", "late_fee_type",
            # Occupancy
            "max_occupants", "pets_allowed", "max_pets",
            # Policies
            "smoking_allowed", "subletting_allowed",
            "renters_insurance_required", "renters_insurance_minimum",
            # Utilities
            "utilities_included",
            # Renewal
            "auto_renewal", "renewal_notice_days", "rent_increase_notice_days",
            # Parking
            "parking_spaces", "parking_space_numbers",
            # Move-in/out
            "move_in_date", "move_out_date",
            "move_in_inspection_complete", "move_out_inspection_complete",
            # Notes
            "notes",
        ]
        widgets = {
            "unit": forms.Select(attrs={"class": "form-select"}),
            "tenant": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "lease_type": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "move_in_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "move_out_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            # Prospective tenant fields
            "prospective_first_name": forms.TextInput(attrs={"class": "form-control"}),
            "prospective_last_name": forms.TextInput(attrs={"class": "form-control"}),
            "prospective_email": forms.EmailInput(attrs={"class": "form-control"}),
            "prospective_phone": forms.TextInput(attrs={"class": "form-control"}),
            # Rent fields
            "monthly_rent": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "security_deposit": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "rent_due_day": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 28}),
            "grace_period_days": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "late_fee_amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "late_fee_type": forms.Select(attrs={"class": "form-select"}),
            # Occupancy
            "max_occupants": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "max_pets": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            # Insurance
            "renters_insurance_minimum": forms.NumberInput(attrs={"class": "form-control", "step": "1000"}),
            # Renewal
            "renewal_notice_days": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "rent_increase_notice_days": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            # Parking
            "parking_spaces": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "parking_space_numbers": forms.TextInput(attrs={"class": "form-control"}),
            # Notes
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make tenant not required at form level (validation handled in clean)
        self.fields["tenant"].required = False

        # Set tenant_mode based on existing instance
        if self.instance and self.instance.pk:
            if self.instance.tenant:
                self.initial["tenant_mode"] = "existing"
            else:
                self.initial["tenant_mode"] = "new"

        # Ensure all fields have proper CSS classes
        for field_name, field in self.fields.items():
            if field_name == "tenant_mode":
                continue  # Skip radio buttons
            if not field.widget.attrs.get("class"):
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs["class"] = "form-select"
                elif isinstance(field.widget, forms.CheckboxInput):
                    field.widget.attrs["class"] = "form-check-input"
                else:
                    field.widget.attrs["class"] = "form-control"

        # Fields with model defaults should not be required
        # (they'll use model defaults if not provided)
        fields_with_defaults = [
            "late_fee_type", "late_fee_amount", "security_deposit",
            "renters_insurance_minimum", "renewal_notice_days",
            "rent_increase_notice_days", "parking_spaces", "max_occupants",
            "max_pets", "grace_period_days", "rent_due_day",
        ]
        for field_name in fields_with_defaults:
            if field_name in self.fields:
                self.fields[field_name].required = False

    def clean(self):
        cleaned_data = super().clean()
        tenant_mode = cleaned_data.get("tenant_mode")
        tenant = cleaned_data.get("tenant")

        if tenant_mode == "existing":
            if not tenant:
                self.add_error("tenant", "Please select an existing tenant.")
            # Clear prospective fields for existing tenant
            cleaned_data["prospective_first_name"] = ""
            cleaned_data["prospective_last_name"] = ""
            cleaned_data["prospective_email"] = ""
            cleaned_data["prospective_phone"] = ""
        elif tenant_mode == "new":
            # Clear tenant for new tenant mode
            cleaned_data["tenant"] = None
            # Require email for new tenants
            if not cleaned_data.get("prospective_email"):
                self.add_error(
                    "prospective_email",
                    "Email is required for new tenants to send onboarding invitation."
                )
            # Require at least first or last name
            if not cleaned_data.get("prospective_first_name") and not cleaned_data.get("prospective_last_name"):
                self.add_error(
                    "prospective_first_name",
                    "Please provide at least a first or last name for the prospective tenant."
                )

        # Validate lease dates
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "End date cannot be before start date.")

        # Validate move dates
        move_in = cleaned_data.get("move_in_date")
        move_out = cleaned_data.get("move_out_date")
        if move_in and move_out and move_out < move_in:
            self.add_error("move_out_date", "Move-out date cannot be before move-in date.")

        return cleaned_data


class LeaseTermForm(forms.ModelForm):
    class Meta:
        model = LeaseTerm
        fields = ["title", "description", "is_standard"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class LeaseOccupantForm(forms.ModelForm):
    class Meta:
        model = LeaseOccupant
        fields = [
            "first_name", "last_name", "relationship", "date_of_birth",
            "email", "phone", "is_on_lease", "is_cosigner",
            "move_in_date", "move_out_date",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "move_in_date": forms.DateInput(attrs={"type": "date"}),
            "move_out_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        move_in = cleaned_data.get("move_in_date")
        move_out = cleaned_data.get("move_out_date")
        if move_in and move_out and move_out < move_in:
            raise forms.ValidationError("Move-out date cannot be before move-in date.")
        return cleaned_data


class LeasePetForm(forms.ModelForm):
    class Meta:
        model = LeasePet
        fields = [
            "pet_type", "name", "breed", "weight_lbs", "color",
            "is_service_animal", "vaccination_current",
            "pet_deposit", "monthly_pet_rent", "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_pet_deposit(self):
        value = self.cleaned_data.get("pet_deposit")
        if value is not None and value < 0:
            raise forms.ValidationError("Pet deposit cannot be negative.")
        return value

    def clean_monthly_pet_rent(self):
        value = self.cleaned_data.get("monthly_pet_rent")
        if value is not None and value < 0:
            raise forms.ValidationError("Monthly pet rent cannot be negative.")
        return value


class LeaseFeeForm(forms.ModelForm):
    class Meta:
        model = LeaseFee
        fields = [
            "fee_type", "name", "amount", "frequency",
            "is_refundable", "description",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_amount(self):
        value = self.cleaned_data.get("amount")
        if value is not None and value < 0:
            raise forms.ValidationError("Fee amount cannot be negative.")
        return value


class LeaseSignatureForm(forms.ModelForm):
    """Form for creating signature requests."""

    class Meta:
        model = LeaseSignature
        fields = ["signer_type", "signer_name", "signer_email"]


class SignLeaseForm(forms.Form):
    """Form for capturing a signature."""

    typed_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Type your full legal name",
        })
    )
    signature_data = forms.CharField(
        widget=forms.HiddenInput(),
        help_text="Base64 encoded signature image"
    )
    agree_to_terms = forms.BooleanField(
        required=True,
        label="I have read and agree to all terms of this lease agreement"
    )
