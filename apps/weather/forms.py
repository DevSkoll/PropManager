from django import forms

from .models import WeatherAlert, WeatherMonitorConfig, WeatherNotificationRule


class WeatherMonitorConfigForm(forms.ModelForm):
    class Meta:
        model = WeatherMonitorConfig
        fields = [
            "property", "latitude", "longitude", "is_active",
            "polling_interval_hours", "snow_threshold_inches",
            "wind_threshold_mph", "temp_low_threshold_f", "temp_high_threshold_f",
        ]
        widgets = {
            "property": forms.Select(attrs={"class": "form-select"}),
            "latitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001"}),
            "longitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "polling_interval_hours": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "snow_threshold_inches": forms.NumberInput(attrs={"class": "form-control", "step": "0.1"}),
            "wind_threshold_mph": forms.NumberInput(attrs={"class": "form-control", "step": "0.1"}),
            "temp_low_threshold_f": forms.NumberInput(attrs={"class": "form-control", "step": "0.1"}),
            "temp_high_threshold_f": forms.NumberInput(attrs={"class": "form-control", "step": "0.1"}),
        }


class WeatherNotificationRuleForm(forms.ModelForm):
    class Meta:
        model = WeatherNotificationRule
        fields = [
            "name", "alert_type", "severity", "property",
            "subject_template", "message_template",
            "is_active", "cooldown_hours",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "alert_type": forms.Select(attrs={"class": "form-select"}),
            "severity": forms.Select(attrs={"class": "form-select"}),
            "property": forms.Select(attrs={"class": "form-select"}),
            "subject_template": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "{alert_type} Alert: {property_name}",
            }),
            "message_template": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": (
                    "Snowfall of {snow_inches}\" expected at {property_name}. "
                    "Please ensure walkways and roadways are cleared for plowing services."
                ),
            }),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "cooldown_hours": forms.NumberInput(attrs={
                "class": "form-control", "min": "0", "max": "168",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["property"].required = False
        self.fields["property"].empty_label = "-- All Properties --"


class WeatherAlertForm(forms.ModelForm):
    class Meta:
        model = WeatherAlert
        fields = [
            "property", "alert_type", "severity", "title", "message",
        ]
        widgets = {
            "property": forms.Select(attrs={"class": "form-select"}),
            "alert_type": forms.Select(attrs={"class": "form-select"}),
            "severity": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }
