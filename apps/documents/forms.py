from django import forms

from .models import Document, DocumentFolder
from .validators import validate_document_file


class DocumentForm(forms.ModelForm):
    """Admin document upload/edit form."""

    class Meta:
        model = Document
        fields = [
            "title", "document_type", "category", "file", "folder",
            "property", "unit", "lease", "tenant", "work_order",
            "is_tenant_visible", "description",
        ]

    def clean_file(self):
        f = self.cleaned_data.get("file")
        if f:
            validate_document_file(f)
        return f


class TenantDocumentUploadForm(forms.ModelForm):
    """Restricted upload form for tenants."""

    TENANT_DOCUMENT_TYPE_CHOICES = [
        ("receipt", "Receipt"),
        ("insurance", "Insurance"),
        ("photo", "Photo"),
        ("other", "Other"),
    ]

    document_type = forms.ChoiceField(choices=TENANT_DOCUMENT_TYPE_CHOICES)

    class Meta:
        model = Document
        fields = ["title", "document_type", "file", "folder", "description"]

    def __init__(self, *args, unit=None, **kwargs):
        super().__init__(*args, **kwargs)
        if unit:
            self.fields["folder"].queryset = DocumentFolder.objects.filter(
                unit=unit, is_tenant_visible=True
            )
        else:
            self.fields["folder"].queryset = DocumentFolder.objects.none()
        self.fields["folder"].required = False

    def clean_file(self):
        f = self.cleaned_data.get("file")
        if f:
            validate_document_file(f)
        return f


class DocumentFolderForm(forms.ModelForm):
    """Admin folder creation/edit form."""

    class Meta:
        model = DocumentFolder
        fields = ["name", "unit", "lease", "is_tenant_visible", "description"]


class TenantFolderForm(forms.ModelForm):
    """Tenant folder creation form - unit/lease auto-set by view."""

    class Meta:
        model = DocumentFolder
        fields = ["name", "description"]
