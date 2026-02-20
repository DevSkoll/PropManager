from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model

from .models import Document, DocumentFolder, EDocument, EDocumentTemplate
from .validators import validate_document_file

User = get_user_model()


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


# =============================================================================
# eDocument Forms
# =============================================================================


class EDocumentTemplateForm(forms.ModelForm):
    """Form for creating/editing eDocument templates."""

    class Meta:
        model = EDocumentTemplate
        fields = ["name", "template_type", "description", "content", "property", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
            "content": forms.Textarea(attrs={
                "rows": 20,
                "class": "markdown-editor",
                "placeholder": "Write your document in markdown format...\n\nUse {{variable_name}} for dynamic content.\nUse [SIGNATURE:Role] for signature blocks.\nUse [INITIALS:Role] for initials blocks.",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["property"].required = False
        self.fields["description"].required = False


class EDocumentCreateForm(forms.ModelForm):
    """Form for creating a new eDocument."""

    class Meta:
        model = EDocument
        fields = ["title", "content", "lease", "tenant", "property"]
        widgets = {
            "content": forms.Textarea(attrs={
                "rows": 20,
                "class": "markdown-editor",
                "placeholder": "Write your document in markdown format...",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lease"].required = False
        self.fields["tenant"].required = False
        self.fields["property"].required = False

        # Limit tenant choices to tenant role users
        self.fields["tenant"].queryset = User.objects.filter(role="tenant", is_active=True)


class EDocumentSendForm(forms.Form):
    """Dynamic form for assigning signers to roles."""

    def __init__(self, *args, edoc=None, required_roles=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.edoc = edoc
        self.required_roles = required_roles or []

        # Get available users
        tenants = User.objects.filter(role="tenant", is_active=True)
        admins = User.objects.filter(role__in=["admin", "manager"], is_active=True)

        # Create fields for each required role
        for role in self.required_roles:
            role_label = role.replace("_", " ").title()

            # User selector
            if role == "landlord":
                user_queryset = admins
            else:
                user_queryset = tenants

            self.fields[f"signer_{role}"] = forms.ModelChoiceField(
                queryset=user_queryset,
                required=False,
                label=f"{role_label} (User Account)",
                help_text="Select a user account or enter details manually below",
            )

            # Name field
            self.fields[f"name_{role}"] = forms.CharField(
                max_length=200,
                required=True,
                label=f"{role_label} Name",
            )

            # Email field
            self.fields[f"email_{role}"] = forms.EmailField(
                required=True,
                label=f"{role_label} Email",
            )

    def clean(self):
        cleaned_data = super().clean()

        # For each role, ensure we have name and email
        for role in self.required_roles:
            user = cleaned_data.get(f"signer_{role}")
            name = cleaned_data.get(f"name_{role}")
            email = cleaned_data.get(f"email_{role}")

            # Auto-fill from user if selected
            if user:
                if not name:
                    cleaned_data[f"name_{role}"] = user.get_full_name() or user.username
                if not email:
                    cleaned_data[f"email_{role}"] = user.email

            # Validate we have required info
            if not cleaned_data.get(f"name_{role}"):
                self.add_error(f"name_{role}", "Name is required.")
            if not cleaned_data.get(f"email_{role}"):
                self.add_error(f"email_{role}", "Email is required.")

        return cleaned_data


class TenantSignatureForm(forms.Form):
    """Form for tenant to submit signature for a block."""

    signature_data = forms.CharField(
        widget=forms.HiddenInput(),
        required=True,
        help_text="Base64 encoded signature image",
    )

    def clean_signature_data(self):
        data = self.cleaned_data.get("signature_data")
        if not data:
            raise forms.ValidationError("Signature is required.")
        if not data.startswith("data:image/"):
            raise forms.ValidationError("Invalid signature format.")
        return data
