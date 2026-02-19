from django import forms

from .models import Property, Unit


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            "name", "property_type", "address_line1", "address_line2",
            "city", "state", "zip_code", "total_units", "is_active", "description",
        ]


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = [
            "unit_number", "bedrooms", "bathrooms", "square_feet",
            "base_rent", "status", "floor", "description",
        ]
