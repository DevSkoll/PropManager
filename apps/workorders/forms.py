from django import forms

from .models import WorkOrder, WorkOrderNote, WorkOrderAttachment


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


ALLOWED_ATTACHMENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
    "application/pdf",
}


class WorkOrderAttachmentForm(forms.ModelForm):
    class Meta:
        model = WorkOrderAttachment
        fields = ["file", "caption"]

    def clean_file(self):
        f = self.cleaned_data.get("file")
        if f:
            if f.content_type not in ALLOWED_ATTACHMENT_TYPES:
                raise forms.ValidationError(
                    "Only image files (JPEG, PNG, GIF, WebP, BMP) and PDFs are allowed."
                )
        return f


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
