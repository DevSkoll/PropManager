"""
Forms for tenant onboarding steps.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

from apps.leases.models import LeaseOccupant, LeasePet

from .models import (
    OnboardingSession,
    OnboardingTemplate,
    OnboardingTemplateDocument,
    OnboardingTemplateFee,
    TenantEmergencyContact,
    TenantEmployment,
    TenantIDVerification,
    TenantInsurance,
    TenantVehicle,
)

User = get_user_model()

phone_validator = RegexValidator(
    regex=r"^\+?1?\d{9,15}$",
    message="Enter a valid phone number.",
)


# =============================================================================
# Admin Forms
# =============================================================================


class OnboardingTemplateForm(forms.ModelForm):
    """Form for creating/editing onboarding templates."""

    class Meta:
        model = OnboardingTemplate
        fields = [
            "name",
            "property",
            "is_active",
            "is_default",
            "collect_vehicles",
            "collect_employment",
            "require_renters_insurance",
            "require_id_verification",
            "welcome_message",
            "property_rules",
            "invitation_email_subject",
            "invitation_email_body",
            "invitation_sms_body",
            "link_expiry_days",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "property": forms.Select(attrs={"class": "form-select"}),
            "welcome_message": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "property_rules": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
            "invitation_email_subject": forms.TextInput(attrs={"class": "form-control"}),
            "invitation_email_body": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 6,
                "placeholder": "Use {{link}} to insert the onboarding URL.",
            }),
            "invitation_sms_body": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Use {{link}} to insert the onboarding URL.",
            }),
            "link_expiry_days": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 90}),
        }


class OnboardingTemplateDocumentForm(forms.ModelForm):
    """Form for adding documents to a template."""

    class Meta:
        model = OnboardingTemplateDocument
        fields = ["edocument_template", "order", "is_required", "description"]
        widgets = {
            "edocument_template": forms.Select(attrs={"class": "form-select"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
        }


class OnboardingTemplateFeeForm(forms.ModelForm):
    """Form for adding fees to a template."""

    class Meta:
        model = OnboardingTemplateFee
        fields = [
            "fee_type",
            "name",
            "description",
            "amount",
            "use_lease_value",
            "lease_field",
            "is_required",
            "is_refundable",
            "order",
        ]
        widgets = {
            "fee_type": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "lease_field": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., monthly_rent, security_deposit",
            }),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }


class OnboardingSessionCreateForm(forms.ModelForm):
    """
    Form for creating a new onboarding session from a pending lease.

    The lease must:
    - Have no tenant assigned (pending onboarding)
    - Not have an active onboarding session already

    Prospective tenant info and unit are pulled from the selected lease.
    """

    class Meta:
        model = OnboardingSession
        fields = [
            "lease",
            "template",
            "notes",
        ]
        widgets = {
            "lease": forms.Select(attrs={"class": "form-select"}),
            "template": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
        labels = {
            "lease": "Select Lease (Pending Onboarding)",
        }
        help_texts = {
            "lease": "Only leases without an assigned tenant are shown.",
            "template": "Onboarding template to use. If blank, the property's default will be used.",
            "notes": "Internal notes (not visible to tenant).",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter leases to only show pending onboarding
        self._filter_lease_queryset()
        self.fields["lease"].required = True
        self.fields["template"].required = False

    def _filter_lease_queryset(self):
        """Filter leases to only show those available for onboarding."""
        from apps.leases.models import Lease

        # Get leases with active onboarding sessions
        active_session_lease_ids = OnboardingSession.objects.filter(
            status__in=["pending", "in_progress"]
        ).values_list("lease_id", flat=True)

        # Filter to leases that:
        # - Have no tenant (pending onboarding)
        # - Have prospective email (required to send invitation)
        # - Don't have an active onboarding session
        self.fields["lease"].queryset = Lease.objects.filter(
            tenant__isnull=True,
        ).exclude(
            prospective_email=""
        ).exclude(
            pk__in=active_session_lease_ids
        ).select_related("unit", "unit__property").order_by("-created_at")

    def clean_lease(self):
        """Validate the selected lease."""
        lease = self.cleaned_data.get("lease")
        if not lease:
            raise forms.ValidationError("Please select a lease pending onboarding.")

        if lease.tenant:
            raise forms.ValidationError("This lease already has a tenant assigned.")

        if not lease.prospective_email:
            raise forms.ValidationError(
                "This lease has no prospective email. "
                "Edit the lease to add an email before starting onboarding."
            )

        # Check for existing active session
        existing = OnboardingSession.objects.filter(
            lease=lease,
            status__in=["pending", "in_progress"],
        ).exists()
        if existing:
            raise forms.ValidationError(
                "An onboarding session already exists for this lease."
            )

        return lease


# =============================================================================
# Onboarding Step Forms
# =============================================================================


class OTPVerificationForm(forms.Form):
    """Form for OTP code entry."""

    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-lg text-center",
            "placeholder": "000000",
            "autocomplete": "one-time-code",
            "inputmode": "numeric",
            "pattern": "[0-9]*",
            "autofocus": True,
        }),
        help_text="Enter the 6-digit code sent to your email.",
    )


class AccountCreationForm(forms.Form):
    """Form for creating a new account during onboarding."""

    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "+1 (555) 123-4567",
        }),
    )
    preferred_contact = forms.ChoiceField(
        choices=[
            ("email", "Email"),
            ("sms", "SMS/Text"),
            ("both", "Both Email and SMS"),
        ],
        initial="email",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number")
        preferred = self.data.get("preferred_contact")
        if preferred in ("sms", "both") and not phone:
            raise forms.ValidationError("Phone number is required for SMS notifications.")
        return phone


class PersonalInfoForm(forms.Form):
    """Form for collecting personal information."""

    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={
            "class": "form-control",
            "type": "date",
        }),
        required=False,
    )
    ssn_last_four = forms.CharField(
        max_length=4,
        min_length=4,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Last 4 digits",
            "inputmode": "numeric",
            "pattern": "[0-9]*",
        }),
        help_text="For identity verification only.",
    )
    drivers_license_state = forms.CharField(
        max_length=2,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "CA",
        }),
    )
    drivers_license_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class EmergencyContactForm(forms.ModelForm):
    """Form for emergency contact information."""

    class Meta:
        model = TenantEmergencyContact
        fields = ["name", "relationship", "phone", "email", "address"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "relationship": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., Parent, Spouse, Sibling",
            }),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class OccupantForm(forms.ModelForm):
    """Form for adding occupants/household members."""

    class Meta:
        model = LeaseOccupant
        fields = ["first_name", "last_name", "relationship", "date_of_birth", "is_on_lease"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "relationship": forms.Select(attrs={"class": "form-select"}),
            "date_of_birth": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
        }


class PetForm(forms.ModelForm):
    """Form for adding pets."""

    class Meta:
        model = LeasePet
        fields = [
            "name",
            "pet_type",
            "breed",
            "color",
            "weight_lbs",
            "is_service_animal",
            "vaccination_current",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "pet_type": forms.Select(attrs={"class": "form-select"}),
            "breed": forms.TextInput(attrs={"class": "form-control"}),
            "color": forms.TextInput(attrs={"class": "form-control"}),
            "weight_lbs": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }


class VehicleForm(forms.ModelForm):
    """Form for adding vehicles."""

    class Meta:
        model = TenantVehicle
        fields = [
            "vehicle_type",
            "make",
            "model",
            "year",
            "color",
            "license_plate",
            "state",
            "is_primary",
        ]
        widgets = {
            "vehicle_type": forms.Select(attrs={"class": "form-select"}),
            "make": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Toyota"}),
            "model": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Camry"}),
            "year": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1900,
                "max": 2030,
            }),
            "color": forms.TextInput(attrs={"class": "form-control"}),
            "license_plate": forms.TextInput(attrs={"class": "form-control"}),
            "state": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "CA",
                "maxlength": 2,
            }),
        }


class EmploymentForm(forms.ModelForm):
    """Form for employment information."""

    class Meta:
        model = TenantEmployment
        fields = [
            "employment_type",
            "employer_name",
            "employer_phone",
            "employer_address",
            "job_title",
            "start_date",
            "gross_income",
            "income_frequency",
            "additional_income",
            "additional_income_source",
        ]
        widgets = {
            "employment_type": forms.Select(attrs={"class": "form-select"}),
            "employer_name": forms.TextInput(attrs={"class": "form-control"}),
            "employer_phone": forms.TextInput(attrs={"class": "form-control"}),
            "employer_address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "job_title": forms.TextInput(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "gross_income": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": 0,
            }),
            "income_frequency": forms.Select(attrs={"class": "form-select"}),
            "additional_income": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": 0,
            }),
            "additional_income_source": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., Rental income, Investments",
            }),
        }


class InsuranceForm(forms.ModelForm):
    """Form for renter's insurance information."""

    class Meta:
        model = TenantInsurance
        fields = [
            "provider_name",
            "policy_number",
            "coverage_amount",
            "liability_coverage",
            "start_date",
            "end_date",
            "policy_document",
        ]
        widgets = {
            "provider_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., State Farm, Lemonade",
            }),
            "policy_number": forms.TextInput(attrs={"class": "form-control"}),
            "coverage_amount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "1000",
                "min": 0,
            }),
            "liability_coverage": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "1000",
                "min": 0,
            }),
            "start_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "end_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "policy_document": forms.FileInput(attrs={
                "class": "form-control",
                "accept": ".pdf,.jpg,.jpeg,.png",
            }),
        }


class InsuranceWaiverForm(forms.Form):
    """Form for waiving renter's insurance requirement."""

    waive_insurance = forms.BooleanField(
        required=True,
        label="I understand and accept the risks",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    acknowledgment = forms.BooleanField(
        required=True,
        label="I acknowledge that I am responsible for my personal belongings",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )


class IDVerificationForm(forms.ModelForm):
    """Form for ID verification upload."""

    class Meta:
        model = TenantIDVerification
        fields = [
            "id_type",
            "id_number",
            "issuing_state",
            "expiration_date",
            "front_image",
            "back_image",
        ]
        widgets = {
            "id_type": forms.Select(attrs={"class": "form-select"}),
            "id_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Last 4 digits only",
                "maxlength": 4,
            }),
            "issuing_state": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "CA",
            }),
            "expiration_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "front_image": forms.FileInput(attrs={
                "class": "form-control",
                "accept": "image/*",
            }),
            "back_image": forms.FileInput(attrs={
                "class": "form-control",
                "accept": "image/*",
            }),
        }
        help_texts = {
            "id_number": "For security, only enter the last 4 characters.",
            "back_image": "Required for driver's licenses and state IDs.",
        }


class MoveInScheduleForm(forms.Form):
    """Form for scheduling move-in date/time."""

    move_in_date = forms.DateField(
        widget=forms.DateInput(attrs={
            "class": "form-control",
            "type": "date",
        }),
    )
    preferred_time = forms.ChoiceField(
        choices=[
            ("morning", "Morning (9am - 12pm)"),
            ("afternoon", "Afternoon (12pm - 4pm)"),
            ("evening", "Evening (4pm - 7pm)"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    special_requests = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Any special requests or notes for move-in day?",
        }),
    )


class StepConfigForm(forms.Form):
    """Dynamic form for step configuration in templates."""

    STEP_CHOICES = [
        ("account_creation", "Account Creation"),
        ("personal_info", "Personal Information"),
        ("emergency_contacts", "Emergency Contacts"),
        ("occupants", "Occupants/Household Members"),
        ("pets", "Pets"),
        ("vehicles", "Vehicles"),
        ("employment", "Employment/Income"),
        ("insurance", "Renter's Insurance"),
        ("id_verification", "ID Verification"),
        ("documents", "Document Signing"),
        ("payments", "Payments"),
        ("move_in_schedule", "Move-In Scheduling"),
        ("welcome", "Welcome/Completion"),
    ]

    def __init__(self, *args, steps_config=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Create fields for each step
        for step_key, step_label in self.STEP_CHOICES:
            config = (steps_config or {}).get(step_key, {})

            self.fields[f"{step_key}_enabled"] = forms.BooleanField(
                required=False,
                initial=config.get("enabled", True),
                label=f"Enable {step_label}",
                widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
            )
            self.fields[f"{step_key}_required"] = forms.BooleanField(
                required=False,
                initial=config.get("required", False),
                label="Required",
                widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
            )
            self.fields[f"{step_key}_order"] = forms.IntegerField(
                initial=config.get("order", self.STEP_CHOICES.index((step_key, step_label)) + 1),
                min_value=1,
                max_value=20,
                widget=forms.NumberInput(attrs={"class": "form-control form-control-sm", "style": "width: 60px"}),
            )

    def get_steps_config(self):
        """Convert form data back to steps_config dict."""
        config = {}
        for step_key, _ in self.STEP_CHOICES:
            config[step_key] = {
                "enabled": self.cleaned_data.get(f"{step_key}_enabled", True),
                "required": self.cleaned_data.get(f"{step_key}_required", False),
                "order": self.cleaned_data.get(f"{step_key}_order", 99),
            }
        return config
