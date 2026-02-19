from django import forms

from .models import Lease, LeaseTerm


class LeaseForm(forms.ModelForm):
    class Meta:
        model = Lease
        fields = [
            "unit", "tenant", "status", "lease_type", "start_date",
            "end_date", "monthly_rent", "security_deposit", "notes",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class LeaseTermForm(forms.ModelForm):
    class Meta:
        model = LeaseTerm
        fields = ["title", "description", "is_standard"]
