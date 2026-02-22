from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import FileExtensionValidator

from apps.accounts.models import User


class AdminAccountForm(UserCreationForm):
    """Form for creating the initial admin account during setup."""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "admin@example.com"}
        ),
    )
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "First Name"}
        ),
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Last Name"}
        ),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if "class" not in field.widget.attrs:
                field.widget.attrs["class"] = "form-control"
            # Add placeholders
            if field_name == "username":
                field.widget.attrs["placeholder"] = "Choose a username"
            elif field_name == "password1":
                field.widget.attrs["placeholder"] = "Choose a strong password"
            elif field_name == "password2":
                field.widget.attrs["placeholder"] = "Confirm your password"

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "admin"
        user.is_staff = True
        user.is_superuser = True
        if commit:
            user.save()
        return user


class EmailConfigForm(forms.Form):
    """Form for configuring email settings during setup."""

    email_host = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "smtp.example.com"}
        ),
    )
    email_port = forms.IntegerField(
        initial=587,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    email_host_user = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "user@example.com"}
        ),
    )
    email_host_password = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "App password or API key"}
        ),
    )
    default_from_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "noreply@example.com"}
        ),
    )
    email_use_tls = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    email_use_ssl = forms.BooleanField(
        initial=False,
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        host = cleaned_data.get("email_host")
        user = cleaned_data.get("email_host_user")
        password = cleaned_data.get("email_host_password")
        from_email = cleaned_data.get("default_from_email")

        # If any field is filled, require all essential fields
        if any([host, user, password, from_email]):
            if not all([host, user, password, from_email]):
                raise forms.ValidationError(
                    "Please fill in all email configuration fields or leave them all empty."
                )

        return cleaned_data


class SMSConfigForm(forms.Form):
    """Form for configuring Twilio SMS settings during setup."""

    account_sid = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}
        ),
    )
    auth_token = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Your Twilio auth token"}
        ),
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "+15551234567"}
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        sid = cleaned_data.get("account_sid")
        token = cleaned_data.get("auth_token")
        phone = cleaned_data.get("phone_number")

        # If any field is filled, require all fields
        if any([sid, token, phone]):
            if not all([sid, token, phone]):
                raise forms.ValidationError(
                    "Please fill in all SMS configuration fields or leave them all empty."
                )

        return cleaned_data


class CSVUploadForm(forms.Form):
    """Form for CSV file uploads during data import step."""

    csv_file = forms.FileField(
        required=True,
        validators=[FileExtensionValidator(allowed_extensions=["csv"])],
        widget=forms.FileInput(
            attrs={"class": "form-control", "accept": ".csv"}
        ),
    )

    def clean_csv_file(self):
        file = self.cleaned_data["csv_file"]
        # 10MB limit
        if file.size > 10 * 1024 * 1024:
            raise forms.ValidationError("File size must be under 10MB.")
        return file


class PaymentGatewaySelectForm(forms.Form):
    """Form for selecting which payment gateway to configure."""

    PROVIDER_CHOICES = [
        ("stripe", "Stripe"),
        ("paypal", "PayPal"),
        ("square", "Square"),
        ("authorize_net", "Authorize.Net"),
        ("braintree", "Braintree"),
        ("plaid", "Plaid (ACH)"),
        ("bitcoin", "Bitcoin"),
    ]

    provider = forms.ChoiceField(
        choices=PROVIDER_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
    )
    display_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Display name for tenants"}
        ),
    )


class IntegrationSettingsForm(forms.Form):
    """Form for enabling/disabling optional integrations."""

    enable_ai = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Enable AI Assistant",
        help_text="Use AI to help with lease analysis, communication drafting, and more.",
    )
    ai_provider = forms.ChoiceField(
        required=False,
        choices=[
            ("", "Select a provider"),
            ("openai", "OpenAI (GPT-4)"),
            ("anthropic", "Anthropic (Claude)"),
            ("google", "Google (Gemini)"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    ai_api_key = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "API key"}
        ),
    )

    enable_weather = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Enable Weather Alerts",
        help_text="Send weather-related notifications to tenants.",
    )
    weather_api_key = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "OpenWeatherMap API key"}
        ),
    )

    enable_rewards = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Enable Tenant Rewards",
        help_text="Reward tenants for on-time payments and engagement.",
    )

    def clean(self):
        cleaned_data = super().clean()

        # If AI enabled, require provider and API key
        if cleaned_data.get("enable_ai"):
            if not cleaned_data.get("ai_provider"):
                self.add_error("ai_provider", "Please select an AI provider.")
            if not cleaned_data.get("ai_api_key"):
                self.add_error("ai_api_key", "Please enter your AI API key.")

        # If weather enabled, require API key
        if cleaned_data.get("enable_weather"):
            if not cleaned_data.get("weather_api_key"):
                self.add_error(
                    "weather_api_key", "Please enter your OpenWeatherMap API key."
                )

        return cleaned_data


class DataImportChoiceForm(forms.Form):
    """Form for choosing data import method."""

    IMPORT_CHOICE = [
        ("skip", "Skip - I'll add data manually later"),
        ("demo", "Load Demo Data - Sample properties, units, and tenants"),
        ("import", "Import from CSV - Upload my existing data"),
    ]

    import_choice = forms.ChoiceField(
        choices=IMPORT_CHOICE,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        initial="skip",
    )
