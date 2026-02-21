"""
Views for linking/unlinking documents to leases.
"""
import mimetypes

from django import forms
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.decorators import admin_required
from apps.documents.models import Document, EDocument
from apps.documents.validators import validate_document_file

from .models import Lease


class LeaseDocumentUploadForm(forms.ModelForm):
    """Simplified form for uploading documents directly to a lease."""

    class Meta:
        model = Document
        fields = ["title", "document_type", "file", "is_tenant_visible", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_file(self):
        f = self.cleaned_data.get("file")
        if f:
            validate_document_file(f)
        return f


@admin_required
def lease_available_documents(request, pk):
    """Return documents available to link to a lease (for modal content)."""
    lease = get_object_or_404(Lease.objects.select_related("unit"), pk=pk)

    # Get unit's documents not already linked to this lease
    documents = Document.objects.filter(
        unit=lease.unit,
        deleted_at__isnull=True,
    ).exclude(lease=lease).order_by("-created_at")

    # Get completed eDocuments for unit's leases, not linked to this lease
    edocuments = EDocument.objects.filter(
        lease__unit=lease.unit,
        status="completed",
    ).exclude(lease=lease).order_by("-completed_at")

    return render(request, "leases/_available_documents.html", {
        "documents": documents,
        "edocuments": edocuments,
        "lease": lease,
    })


@admin_required
@require_POST
def lease_link_document(request, pk):
    """Link a document or eDocument to a lease."""
    lease = get_object_or_404(Lease, pk=pk)
    doc_type = request.POST.get("type")
    doc_id = request.POST.get("document_id")

    if not doc_type or not doc_id:
        messages.error(request, "Invalid request.")
        return redirect("leases_admin:lease_detail", pk=pk)

    if doc_type == "document":
        doc = get_object_or_404(Document, pk=doc_id)
        doc.lease = lease
        doc.save(update_fields=["lease", "updated_at"])
        messages.success(request, f'Document "{doc.title}" linked to lease.')

    elif doc_type == "edocument":
        edoc = get_object_or_404(EDocument, pk=doc_id)
        edoc.lease = lease
        edoc.save(update_fields=["lease", "updated_at"])
        messages.success(request, f'eDocument "{edoc.title}" linked to lease.')

    else:
        messages.error(request, "Invalid document type.")

    return redirect("leases_admin:lease_detail", pk=pk)


@admin_required
@require_POST
def lease_unlink_document(request, pk):
    """Unlink a document or eDocument from a lease."""
    lease = get_object_or_404(Lease, pk=pk)
    doc_type = request.POST.get("type")
    doc_id = request.POST.get("document_id")

    if not doc_type or not doc_id:
        messages.error(request, "Invalid request.")
        return redirect("leases_admin:lease_detail", pk=pk)

    if doc_type == "document":
        doc = get_object_or_404(Document, pk=doc_id, lease=lease)
        doc.lease = None
        doc.save(update_fields=["lease", "updated_at"])
        messages.success(request, f'Document "{doc.title}" unlinked from lease.')

    elif doc_type == "edocument":
        edoc = get_object_or_404(EDocument, pk=doc_id, lease=lease)
        edoc.lease = None
        edoc.save(update_fields=["lease", "updated_at"])
        messages.success(request, f'eDocument "{edoc.title}" unlinked from lease.')

    else:
        messages.error(request, "Invalid document type.")

    return redirect("leases_admin:lease_detail", pk=pk)


@admin_required
@require_POST
def lease_link_multiple_documents(request, pk):
    """Link multiple documents to a lease at once (from modal selection)."""
    lease = get_object_or_404(Lease, pk=pk)

    # Get selected document IDs
    document_ids = request.POST.getlist("document_ids")
    edocument_ids = request.POST.getlist("edocument_ids")

    linked_count = 0

    # Link regular documents
    if document_ids:
        documents = Document.objects.filter(pk__in=document_ids, deleted_at__isnull=True)
        for doc in documents:
            doc.lease = lease
            doc.save(update_fields=["lease", "updated_at"])
            linked_count += 1

    # Link eDocuments
    if edocument_ids:
        edocuments = EDocument.objects.filter(pk__in=edocument_ids, status="completed")
        for edoc in edocuments:
            edoc.lease = lease
            edoc.save(update_fields=["lease", "updated_at"])
            linked_count += 1

    if linked_count > 0:
        messages.success(request, f"{linked_count} document(s) linked to lease.")
    else:
        messages.warning(request, "No documents were selected.")

    return redirect("leases_admin:lease_detail", pk=pk)


@admin_required
def lease_upload_document(request, pk):
    """Upload a new document and automatically link it to a lease."""
    lease = get_object_or_404(
        Lease.objects.select_related("unit", "unit__property", "tenant"),
        pk=pk
    )

    if request.method == "POST":
        form = LeaseDocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            # Auto-set lease-related fields
            doc.lease = lease
            doc.unit = lease.unit
            doc.property = lease.unit.property if lease.unit else None
            doc.tenant = lease.tenant
            doc.uploaded_by_role = "admin"
            doc.created_by = request.user

            # Set file metadata
            if doc.file:
                doc.file_size = doc.file.size
                doc.mime_type = mimetypes.guess_type(doc.file.name)[0] or "application/octet-stream"

            doc.save()
            messages.success(request, f'Document "{doc.title}" uploaded and linked to lease.')
            return redirect("leases_admin:lease_detail", pk=pk)
    else:
        form = LeaseDocumentUploadForm(initial={"is_tenant_visible": True})

    return render(request, "leases/_upload_document_form.html", {
        "form": form,
        "lease": lease,
    })
