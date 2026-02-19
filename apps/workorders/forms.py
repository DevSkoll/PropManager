from django import forms

from .models import WorkOrder, WorkOrderNote, WorkOrderImage


class WorkOrderForm(forms.ModelForm):
    class Meta:
        model = WorkOrder
        fields = ["title", "description", "unit", "priority", "category", "scheduled_date"]
        widgets = {
            "scheduled_date": forms.DateInput(attrs={"type": "date"}),
        }


class WorkOrderNoteForm(forms.ModelForm):
    class Meta:
        model = WorkOrderNote
        fields = ["text", "is_internal"]


class WorkOrderImageForm(forms.ModelForm):
    class Meta:
        model = WorkOrderImage
        fields = ["image", "caption"]
