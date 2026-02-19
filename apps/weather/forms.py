from django import forms

from .models import WeatherMonitorConfig


class WeatherMonitorConfigForm(forms.ModelForm):
    class Meta:
        model = WeatherMonitorConfig
        fields = [
            "property", "latitude", "longitude", "is_active",
            "polling_interval_hours", "snow_threshold_inches",
            "wind_threshold_mph", "temp_low_threshold_f", "temp_high_threshold_f",
        ]
