from django import forms

from .models import TenantProfile


class TenantProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    phone_number = forms.CharField(max_length=20, required=False)
    preferred_contact = forms.ChoiceField(
        choices=[("email", "Email"), ("sms", "SMS")], required=False
    )

    class Meta:
        model = TenantProfile
        fields = ["emergency_contact_name", "emergency_contact_phone", "notes"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name
            self.fields["phone_number"].initial = user.phone_number
            self.fields["preferred_contact"].initial = user.preferred_contact


class TenantLoginForm(forms.Form):
    identifier = forms.CharField(
        label="Email or Phone Number",
        max_length=254,
        widget=forms.TextInput(attrs={"placeholder": "Enter your email or phone number", "autofocus": True}),
    )


class OTPVerifyForm(forms.Form):
    code = forms.CharField(
        label="Verification Code",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={"placeholder": "Enter 6-digit code", "autofocus": True, "autocomplete": "one-time-code"}),
    )


class AdminLoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Username", "autofocus": True}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password"}),
    )
