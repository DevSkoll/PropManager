from django import forms

from .models import Lease, LeaseFee, LeaseOccupant, LeasePet, LeaseSignature, LeaseTerm


class LeaseForm(forms.ModelForm):
    class Meta:
        model = Lease
        fields = [
            # Core
            "unit", "tenant", "status", "lease_type", "start_date", "end_date",
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
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "move_in_date": forms.DateInput(attrs={"type": "date"}),
            "move_out_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


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
