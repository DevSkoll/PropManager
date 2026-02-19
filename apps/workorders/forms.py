from django import forms

from .models import WorkOrder, WorkOrderNote, WorkOrderImage


class WorkOrderForm(forms.ModelForm):
    class Meta:
        model = WorkOrder
        fields = ["title", "description", "unit", "priority", "category", "scheduled_date"]
        widgets = {
            "scheduled_date": forms.DateInput(attrs={"type": "date"}),
        }


class TenantWorkOrderForm(forms.ModelForm):
    class Meta:
        model = WorkOrder
        fields = ["title", "description", "priority", "category"]


class WorkOrderNoteForm(forms.ModelForm):
    class Meta:
        model = WorkOrderNote
        fields = ["text", "is_internal"]


class WorkOrderImageForm(forms.ModelForm):
    class Meta:
        model = WorkOrderImage
        fields = ["image", "caption"]


class ContractorAssignForm(forms.Form):
    contractor_name = forms.CharField(max_length=200)
    phone = forms.CharField(max_length=20, required=False)
    email = forms.EmailField(required=False)
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
    expiry_days = forms.IntegerField(initial=30, min_value=1, max_value=365)


class WorkOrderStatusForm(forms.Form):
    new_status = forms.ChoiceField(choices=WorkOrder.STATUS_CHOICES)


class ContractorStatusForm(forms.Form):
    new_status = forms.ChoiceField(choices=[
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
    ])
