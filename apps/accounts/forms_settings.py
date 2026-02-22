"""
Forms for system settings management.
Bryce at JCU//JEDI
arctek.us
"""

from django import forms
from apps.core.models import SystemSettings


class SystemSettingsForm(forms.ModelForm):
    """Form for editing system-wide settings."""
    
    class Meta:
        model = SystemSettings
        fields = ["openweathermap_api_key"]
        widgets = {
            "openweathermap_api_key": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter your OpenWeatherMap API key"
            })
        }
        labels = {
            "openweathermap_api_key": "OpenWeatherMap API Key"
        }
