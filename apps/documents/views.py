import mimetypes

from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.decorators import admin_required, tenant_required

from .forms import DocumentForm
from .models import Document, DocumentCategory


# ---------------------------------------------------------------------------
# Admin views
# ---------------------------------------------------------------------------


@admin_required
def admin_document_list(request):
    """List all documents with optional filters by document_type and category."""
    qs = Document.objects.select_related(
        "category", "property", "unit", "lease", "tenant", "work_order", "created_by",
    ).order_by("-created_at")

    document_type = request.GET.get("type", "")
    category_id = request.GET.get("category", "")

    if document_type:
        qs = qs.filter(document_type=document_type)
    if category_id:
        qs = qs.filter(category_id=category_id)

    categories = DocumentCategory.objects.all()

    context = {
        "documents": qs,
        "document_type_choices": Document.DOCUMENT_TYPE_CHOICES,
        "categories": categories,
        "selected_type": document_type,
        "selected_category": category_id,
    }
    return render(request, "documents/admin_document_list.html", context)


@admin_required
def admin_document_upload(request):
    """Upload a new document with metadata."""
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            uploaded_file = request.FILES["file"]
            document.file_size = uploaded_file.size
            document.mime_type = (
                uploaded_file.content_type
                or mimetypes.guess_type(uploaded_file.name)[0]
                or "application/octet-stream"
            )
            document.created_by = request.user
            document.updated_by = request.user
            document.save()
            messages.success(request, f'Document "{document.title}" uploaded successfully.')
            return redirect("documents_admin:document_detail", pk=document.pk)
    else:
        form = DocumentForm()

    return render(request, "documents/admin_document_upload.html", {"form": form})


@admin_required
def admin_document_detail(request, pk):
    """View document details."""
    document = get_object_or_404(
        Document.objects.select_related(
            "category", "property", "unit", "lease", "tenant", "work_order",
            "created_by", "updated_by",
        ),
        pk=pk,
    )
    return render(request, "documents/admin_document_detail.html", {"document": document})


@admin_required
def admin_document_delete(request, pk):
    """Delete a document (POST only)."""
    document = get_object_or_404(Document, pk=pk)
    if request.method == "POST":
        title = document.title
        document.file.delete(save=False)
        document.delete()
        messages.success(request, f'Document "{title}" has been deleted.')
        return redirect("documents_admin:document_list")
    return redirect("documents_admin:document_detail", pk=pk)


@admin_required
def admin_document_download(request, pk):
    """Serve file download for admin users."""
    document = get_object_or_404(Document, pk=pk)
    if not document.file:
        raise Http404("No file attached to this document.")
    response = FileResponse(
        document.file.open("rb"),
        content_type=document.mime_type or "application/octet-stream",
    )
    response["Content-Disposition"] = f'attachment; filename="{document.file.name.split("/")[-1]}"'
    return response


# ---------------------------------------------------------------------------
# Tenant views
# ---------------------------------------------------------------------------


@tenant_required
def tenant_document_list(request):
    """List documents visible to the current tenant."""
    documents = (
        Document.objects.filter(is_tenant_visible=True, tenant=request.user)
        .select_related("category")
        .order_by("-created_at")
    )
    return render(request, "documents/tenant_document_list.html", {"documents": documents})


@tenant_required
def tenant_document_download(request, pk):
    """Download a document after verifying tenant access."""
    document = get_object_or_404(
        Document,
        pk=pk,
        is_tenant_visible=True,
        tenant=request.user,
    )
    if not document.file:
        raise Http404("No file attached to this document.")
    response = FileResponse(
        document.file.open("rb"),
        content_type=document.mime_type or "application/octet-stream",
    )
    response["Content-Disposition"] = f'attachment; filename="{document.file.name.split("/")[-1]}"'
    return response
