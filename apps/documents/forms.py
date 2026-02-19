from django import forms

from .models import Document


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = [
            "title", "document_type", "category", "file",
            "property", "unit", "lease", "tenant", "work_order",
            "is_tenant_visible", "description",
        ]
