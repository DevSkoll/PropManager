from django import forms


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
