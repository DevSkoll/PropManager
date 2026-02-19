import mimetypes

from django.contrib import messages
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.decorators import admin_required, tenant_required

from .forms import DocumentFolderForm, DocumentForm, TenantDocumentUploadForm, TenantFolderForm
from .models import Document, DocumentCategory, DocumentFolder
from .validators import validate_document_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _verify_tenant_document_access(user, document):
    """Verify a tenant has access to a document.

    Access is granted if:
    - The document's tenant field matches the user, OR
    - The document's unit matches one of the user's active leases' units

    Raises Http404 (not 403) to prevent IDOR information leakage.
    """
    if document.tenant == user:
        return
    from apps.leases.models import Lease
    tenant_unit_ids = Lease.objects.filter(
        tenant=user, status="active"
    ).values_list("unit_id", flat=True)
    if document.unit_id and document.unit_id in tenant_unit_ids:
        return
    raise Http404


def _secure_download_response(document):
    """Build a FileResponse with security headers."""
    if not document.file:
        raise Http404("No file attached to this document.")
    response = FileResponse(
        document.file.open("rb"),
        content_type=document.mime_type or "application/octet-stream",
    )
    filename = document.file.name.split("/")[-1]
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'"
    return response


def _inline_preview_response(document):
    """Build a FileResponse for inline preview (images and PDFs only)."""
    if not document.file:
        raise Http404("No file attached to this document.")
    preview_type = document.preview_type()
    if preview_type not in ("image", "pdf"):
        raise Http404
    response = FileResponse(
        document.file.open("rb"),
        content_type=document.mime_type,
    )
    filename = document.file.name.split("/")[-1]
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _read_text_preview(document, max_bytes=100 * 1024):
    """Read up to max_bytes of a text file and return as a string."""
    if document.preview_type() != "text" or not document.file:
        return None
    try:
        with document.file.open("rb") as f:
            raw = f.read(max_bytes)
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Admin views
# ---------------------------------------------------------------------------


@admin_required
def admin_document_list(request):
    """List all documents with optional filters, search, and deleted tab."""
    show_deleted = request.GET.get("show_deleted") == "1"
    search_query = request.GET.get("q", "").strip()

    if show_deleted:
        qs = Document.all_objects.filter(deleted_at__isnull=False).select_related(
            "category", "property", "unit", "lease", "tenant", "work_order",
            "created_by", "folder", "deleted_by",
        ).order_by("-deleted_at")
    else:
        qs = Document.objects.select_related(
            "category", "property", "unit", "lease", "tenant", "work_order",
            "created_by", "folder",
        ).order_by("-created_at")

    document_type = request.GET.get("type", "")
    category_id = request.GET.get("category", "")
    folder_id = request.GET.get("folder", "")

    if document_type:
        qs = qs.filter(document_type=document_type)
    if category_id:
        qs = qs.filter(category_id=category_id)
    if folder_id:
        qs = qs.filter(folder_id=folder_id)
    if search_query:
        qs = qs.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(file__icontains=search_query)
        )

    categories = DocumentCategory.objects.all()
    folders = DocumentFolder.objects.all()

    context = {
        "documents": qs,
        "document_type_choices": Document.DOCUMENT_TYPE_CHOICES,
        "categories": categories,
        "folders": folders,
        "selected_type": document_type,
        "selected_category": category_id,
        "selected_folder": folder_id,
        "show_deleted": show_deleted,
        "search_query": search_query,
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
            document.uploaded_by_role = "admin"
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
    """View document details (including soft-deleted via all_objects)."""
    document = get_object_or_404(
        Document.all_objects.select_related(
            "category", "property", "unit", "lease", "tenant", "work_order",
            "created_by", "updated_by", "folder", "deleted_by", "locked_by",
        ),
        pk=pk,
    )
    context = {
        "document": document,
        "text_preview": _read_text_preview(document),
    }
    return render(request, "documents/admin_document_detail.html", context)


@admin_required
def admin_document_delete(request, pk):
    """Soft-delete a document (POST only). Respects lock."""
    document = get_object_or_404(Document, pk=pk)
    if request.method == "POST":
        if document.is_locked:
            messages.error(request, f'Document "{document.title}" is locked and cannot be deleted.')
            return redirect("documents_admin:document_detail", pk=pk)
        document.soft_delete(user=request.user)
        messages.success(request, f'Document "{document.title}" has been moved to trash.')
        return redirect("documents_admin:document_list")
    return redirect("documents_admin:document_detail", pk=pk)


@admin_required
def admin_document_restore(request, pk):
    """Restore a soft-deleted document (POST only)."""
    document = get_object_or_404(Document.all_objects, pk=pk, deleted_at__isnull=False)
    if request.method == "POST":
        document.restore()
        messages.success(request, f'Document "{document.title}" has been restored.')
        return redirect("documents_admin:document_detail", pk=pk)
    return redirect("documents_admin:document_detail", pk=pk)


@admin_required
def admin_document_permanent_delete(request, pk):
    """Permanently delete a document (POST only)."""
    document = get_object_or_404(Document.all_objects, pk=pk)
    if request.method == "POST":
        if document.is_locked:
            messages.error(request, f'Document "{document.title}" is locked and cannot be deleted.')
            return redirect("documents_admin:document_detail", pk=pk)
        title = document.title
        document.file.delete(save=False)
        document.delete()
        messages.success(request, f'Document "{title}" has been permanently deleted.')
        return redirect("documents_admin:document_list")
    return redirect("documents_admin:document_detail", pk=pk)


@admin_required
def admin_document_download(request, pk):
    """Serve file download for admin users."""
    document = get_object_or_404(Document.all_objects, pk=pk)
    return _secure_download_response(document)


@admin_required
def admin_document_preview(request, pk):
    """Serve file inline for preview (images and PDFs only)."""
    document = get_object_or_404(Document.all_objects, pk=pk)
    return _inline_preview_response(document)


@admin_required
def admin_document_lock(request, pk):
    """Lock a document (POST only)."""
    document = get_object_or_404(Document, pk=pk)
    if request.method == "POST":
        document.lock(request.user)
        messages.success(request, f'Document "{document.title}" has been locked.')
    return redirect("documents_admin:document_detail", pk=pk)


@admin_required
def admin_document_unlock(request, pk):
    """Unlock a document (POST only)."""
    document = get_object_or_404(Document.all_objects, pk=pk)
    if request.method == "POST":
        document.unlock()
        messages.success(request, f'Document "{document.title}" has been unlocked.')
    return redirect("documents_admin:document_detail", pk=pk)


# ---------------------------------------------------------------------------
# Admin folder views
# ---------------------------------------------------------------------------


@admin_required
def admin_folder_list(request):
    """List all document folders."""
    folders = DocumentFolder.objects.select_related("unit", "unit__property", "lease").order_by("name")
    return render(request, "documents/admin_folder_list.html", {"folders": folders})


@admin_required
def admin_folder_create(request):
    """Create a new document folder."""
    if request.method == "POST":
        form = DocumentFolderForm(request.POST)
        if form.is_valid():
            folder = form.save(commit=False)
            folder.created_by = request.user
            folder.updated_by = request.user
            folder.save()
            messages.success(request, f'Folder "{folder.name}" created successfully.')
            return redirect("documents_admin:folder_detail", pk=folder.pk)
    else:
        form = DocumentFolderForm()
    return render(request, "documents/admin_folder_form.html", {"form": form})


@admin_required
def admin_folder_detail(request, pk):
    """View folder contents."""
    folder = get_object_or_404(
        DocumentFolder.objects.select_related("unit", "unit__property", "lease"),
        pk=pk,
    )
    documents = Document.objects.filter(folder=folder).select_related(
        "category", "created_by",
    ).order_by("-created_at")
    return render(request, "documents/admin_folder_detail.html", {
        "folder": folder,
        "documents": documents,
    })


# ---------------------------------------------------------------------------
# Tenant views
# ---------------------------------------------------------------------------


def _get_tenant_active_lease(user):
    """Return the tenant's active lease (first found), or None."""
    from apps.leases.models import Lease
    return Lease.objects.filter(tenant=user, status="active").select_related("unit").first()


@tenant_required
def tenant_document_list(request):
    """List documents visible to the current tenant, with folder browsing and search."""
    lease = _get_tenant_active_lease(request.user)
    search_query = request.GET.get("q", "").strip()
    folder_id = request.GET.get("folder", "")

    if lease:
        # Documents visible to tenant: shared by admin OR uploaded by tenant themselves
        qs = Document.objects.filter(
            Q(is_tenant_visible=True, unit=lease.unit)
            | Q(is_tenant_visible=True, tenant=request.user)
            | Q(created_by=request.user, uploaded_by_role="tenant")
        ).distinct().select_related("category", "folder", "created_by").order_by("-created_at")

        folders = DocumentFolder.objects.filter(
            unit=lease.unit, is_tenant_visible=True
        )
    else:
        qs = Document.objects.filter(
            Q(is_tenant_visible=True, tenant=request.user)
            | Q(created_by=request.user, uploaded_by_role="tenant")
        ).distinct().select_related("category", "folder", "created_by").order_by("-created_at")
        folders = DocumentFolder.objects.none()

    if folder_id:
        qs = qs.filter(folder_id=folder_id)
    if search_query:
        qs = qs.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
        )

    context = {
        "documents": qs,
        "folders": folders,
        "selected_folder": folder_id,
        "search_query": search_query,
        "lease": lease,
    }
    return render(request, "documents/tenant_document_list.html", context)


@tenant_required
def tenant_document_upload(request):
    """Upload a document as a tenant."""
    lease = _get_tenant_active_lease(request.user)
    if not lease:
        messages.error(request, "You need an active lease to upload documents.")
        return redirect("documents_tenant:document_list")

    if request.method == "POST":
        form = TenantDocumentUploadForm(request.POST, request.FILES, unit=lease.unit)
        if form.is_valid():
            document = form.save(commit=False)
            uploaded_file = request.FILES["file"]
            document.file_size = uploaded_file.size
            document.mime_type = (
                uploaded_file.content_type
                or mimetypes.guess_type(uploaded_file.name)[0]
                or "application/octet-stream"
            )
            document.unit = lease.unit
            document.lease = lease
            document.tenant = request.user
            document.uploaded_by_role = "tenant"
            document.is_tenant_visible = True
            document.created_by = request.user
            document.updated_by = request.user
            document.save()
            messages.success(request, f'Document "{document.title}" uploaded successfully.')
            return redirect("documents_tenant:document_detail", pk=document.pk)
    else:
        form = TenantDocumentUploadForm(unit=lease.unit)

    return render(request, "documents/tenant_document_upload.html", {"form": form})


@tenant_required
def tenant_document_detail(request, pk):
    """View document detail as a tenant."""
    document = get_object_or_404(
        Document.objects.select_related(
            "category", "folder", "created_by",
        ),
        pk=pk,
    )
    _verify_tenant_document_access(request.user, document)
    is_own_upload = (document.created_by == request.user and document.uploaded_by_role == "tenant")
    return render(request, "documents/tenant_document_detail.html", {
        "document": document,
        "is_own_upload": is_own_upload,
        "text_preview": _read_text_preview(document),
    })


@tenant_required
def tenant_document_delete(request, pk):
    """Soft-delete a tenant's own upload (POST only). Respects lock."""
    document = get_object_or_404(
        Document,
        pk=pk,
        created_by=request.user,
        uploaded_by_role="tenant",
    )
    if request.method == "POST":
        if document.is_locked:
            messages.error(request, "This document is locked and cannot be deleted.")
            return redirect("documents_tenant:document_detail", pk=pk)
        document.soft_delete(user=request.user)
        messages.success(request, f'Document "{document.title}" has been deleted.')
        return redirect("documents_tenant:document_list")
    return redirect("documents_tenant:document_detail", pk=pk)


@tenant_required
def tenant_document_download(request, pk):
    """Download a document after verifying tenant access."""
    document = get_object_or_404(Document, pk=pk)
    _verify_tenant_document_access(request.user, document)
    return _secure_download_response(document)


@tenant_required
def tenant_document_preview(request, pk):
    """Serve file inline for preview after verifying tenant access."""
    document = get_object_or_404(Document, pk=pk)
    _verify_tenant_document_access(request.user, document)
    return _inline_preview_response(document)


@tenant_required
def tenant_folder_create(request):
    """Create a folder scoped to the tenant's unit."""
    lease = _get_tenant_active_lease(request.user)
    if not lease:
        messages.error(request, "You need an active lease to create folders.")
        return redirect("documents_tenant:document_list")

    if request.method == "POST":
        form = TenantFolderForm(request.POST)
        if form.is_valid():
            folder = form.save(commit=False)
            folder.unit = lease.unit
            folder.lease = lease
            folder.is_tenant_visible = True
            folder.created_by = request.user
            folder.updated_by = request.user
            folder.save()
            messages.success(request, f'Folder "{folder.name}" created successfully.')
            return redirect("documents_tenant:document_list")
    else:
        form = TenantFolderForm()

    return render(request, "documents/tenant_folder_form.html", {"form": form})
