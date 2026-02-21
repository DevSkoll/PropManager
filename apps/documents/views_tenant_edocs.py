"""
Tenant views for viewing and signing eDocuments.

Provides views for tenants to view pending eDocuments and sign them
using an e-signature canvas interface.
"""

import markdown
from django.contrib import messages
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.decorators import tenant_required

from .markdown_parser import parse_signature_tags, replace_tags_with_html
from .models import EDocument, EDocumentFillableBlock, EDocumentSigner
from .variables import TemplateVariableResolver


def _get_client_ip(request) -> str:
    """Get client IP address from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _verify_tenant_edoc_access(user, edoc):
    """Verify tenant has access to sign this eDocument.

    Access is granted if:
    - The tenant field matches the user, OR
    - The user is assigned as a signer for this document

    Raises Http404 to prevent IDOR information leakage.
    """
    # Check if user is the tenant on the document
    if edoc.tenant == user:
        return

    # Check if user is assigned as a signer
    if edoc.signers.filter(user=user).exists():
        return

    raise Http404


@tenant_required
def tenant_edoc_list(request):
    """List pending eDocuments for the tenant to sign."""
    user = request.user

    # Get all eDocs where this user is a signer
    signer_doc_ids = EDocumentSigner.objects.filter(
        user=user
    ).values_list("document_id", flat=True)

    # Get eDocs either directly assigned to tenant or via signer
    edocs = EDocument.objects.filter(
        status__in=["pending", "partial"],
    ).filter(
        # Either the tenant field matches or user is a signer
        pk__in=signer_doc_ids
    ).select_related(
        "template", "lease", "edoc_property"
    ).order_by("-sent_at")

    # Also include completed docs for viewing
    completed_edocs = EDocument.objects.filter(
        status="completed",
    ).filter(
        pk__in=signer_doc_ids
    ).select_related(
        "template", "lease", "edoc_property"
    ).order_by("-completed_at")[:10]

    # Separate by signing status for this user
    pending_edocs = []
    for edoc in edocs:
        signer = edoc.signers.filter(user=user).first()
        if signer and not signer.is_signed:
            pending_edocs.append({
                "edoc": edoc,
                "signer": signer,
                "blocks_remaining": signer.blocks.filter(signed_at__isnull=True).count(),
            })

    context = {
        "pending_edocs": pending_edocs,
        "completed_edocs": completed_edocs,
    }
    return render(request, "documents/tenant_edoc_list.html", context)


@tenant_required
def tenant_edoc_detail(request, pk):
    """View eDocument and sign if required."""
    edoc = get_object_or_404(
        EDocument.objects.select_related("template", "lease", "edoc_property"),
        pk=pk
    )
    _verify_tenant_edoc_access(request.user, edoc)

    # Find the signer record for this user
    signer = edoc.signers.filter(user=request.user).first()

    if not signer:
        messages.error(request, "You are not assigned to sign this document.")
        return redirect("documents_tenant:edoc_list")

    # If already signed by this user, show read-only view
    if signer.is_signed:
        return _render_edoc_readonly(request, edoc, signer)

    # Render content with variable substitution
    if edoc.lease:
        resolver = TemplateVariableResolver(
            lease=edoc.lease,
            landlord_user=edoc.created_by,
        )
        rendered_content = resolver.substitute(edoc.content)
    else:
        rendered_content = edoc.content

    # Convert markdown to HTML
    rendered_html = markdown.markdown(
        rendered_content,
        extensions=["tables", "fenced_code"]
    )

    # Get signed blocks for display
    all_blocks = edoc.signature_blocks.select_related("signer").all()
    signed_blocks = {
        block.block_order: block.image
        for block in all_blocks if block.is_signed
    }

    # Get filled blocks for display
    filled_blocks = {
        block.block_order: block.content
        for block in edoc.fillable_blocks.filter(filled_at__isnull=False)
    }

    # Get fillable blocks for this user's role
    user_fillables = edoc.fillable_blocks.filter(
        role=signer.role,
        filled_at__isnull=True
    ).order_by("block_order")

    # Replace tags with HTML (signed/filled ones show content, pending show inputs)
    rendered_html = replace_tags_with_html(
        rendered_html,
        signed_blocks=signed_blocks,
        filled_blocks=filled_blocks,
        current_role=signer.role,
    )

    # Get blocks this user needs to sign
    user_blocks = signer.blocks.filter(signed_at__isnull=True).order_by("block_order")

    context = {
        "edoc": edoc,
        "signer": signer,
        "user_blocks": user_blocks,
        "user_fillables": user_fillables,
        "rendered_html": rendered_html,
        "all_signers": edoc.signers.all(),
        "progress": edoc.signature_progress,
    }
    return render(request, "documents/tenant_edoc_sign.html", context)


def _render_edoc_readonly(request, edoc, signer):
    """Render a read-only view of the signed document."""
    # Render content
    if edoc.lease:
        resolver = TemplateVariableResolver(
            lease=edoc.lease,
            landlord_user=edoc.created_by,
        )
        rendered_content = resolver.substitute(edoc.content)
    else:
        rendered_content = edoc.content

    rendered_html = markdown.markdown(
        rendered_content,
        extensions=["tables", "fenced_code"]
    )

    # Get all signed blocks
    signed_blocks = {
        block.block_order: block.image
        for block in edoc.signature_blocks.filter(signed_at__isnull=False)
    }

    # Get all filled blocks
    filled_blocks = {
        block.block_order: block.content
        for block in edoc.fillable_blocks.filter(filled_at__isnull=False)
    }

    rendered_html = replace_tags_with_html(
        rendered_html,
        signed_blocks=signed_blocks,
        filled_blocks=filled_blocks,
    )

    context = {
        "edoc": edoc,
        "signer": signer,
        "rendered_html": rendered_html,
        "all_signers": edoc.signers.all(),
        "is_readonly": True,
    }
    return render(request, "documents/tenant_edoc_view.html", context)


@tenant_required
@require_POST
def tenant_edoc_sign(request, pk):
    """Process signature and fillable field submission from tenant."""
    edoc = get_object_or_404(EDocument, pk=pk)
    _verify_tenant_edoc_access(request.user, edoc)

    # Find the signer record
    signer = edoc.signers.filter(user=request.user).first()
    if not signer:
        return JsonResponse({"success": False, "error": "Not authorized"}, status=403)

    if signer.is_signed:
        return JsonResponse({"success": False, "error": "Already signed"})

    if edoc.status == "cancelled":
        return JsonResponse({"success": False, "error": "Document was cancelled"})

    # Get signature data
    signature_data = request.POST.get("signature_data")
    if not signature_data:
        return JsonResponse({"success": False, "error": "No signature provided"})

    # Validate signature data format (basic check for base64 PNG)
    if not signature_data.startswith("data:image/png;base64,"):
        return JsonResponse({"success": False, "error": "Invalid signature format"})

    client_ip = _get_client_ip(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
    now = timezone.now()

    try:
        with transaction.atomic():
            # Process fillable fields for this signer's role
            user_fillables = edoc.fillable_blocks.filter(
                role=signer.role,
                filled_at__isnull=True
            )
            for fillable in user_fillables:
                field_name = f"fillable-{signer.role}-{fillable.block_order}"
                content = request.POST.get(field_name, "").strip()
                if content:
                    fillable.content = content
                    fillable.filled_at = now
                    fillable.filled_by = request.user
                    fillable.ip_address = client_ip
                    fillable.save()

            # Update signer record
            signer.signature_image = signature_data
            signer.signed_at = now
            signer.ip_address = client_ip
            signer.user_agent = user_agent
            signer.save()

            # Update all signature blocks for this signer
            signer.blocks.update(
                image=signature_data,
                signed_at=now,
                ip_address=client_ip,
            )

            # Update document status
            if edoc.is_fully_signed:
                edoc.check_completion()
                all_complete = True
                # Send completion notification
                from .notifications import send_document_completed
                send_document_completed(edoc)
            else:
                if edoc.status == "pending":
                    edoc.status = "partial"
                    edoc.save(update_fields=["status"])
                all_complete = False
                # Notify admin and next signer
                from .notifications import send_signature_received
                send_signature_received(edoc, signer)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse({
        "success": True,
        "all_complete": all_complete,
        "redirect": request.build_absolute_uri(
            "/tenant/documents/edocs/" + str(edoc.pk) + "/"
        ),
    })


@tenant_required
def tenant_edoc_download_pdf(request, pk):
    """Download PDF of completed document."""
    edoc = get_object_or_404(EDocument, pk=pk)
    _verify_tenant_edoc_access(request.user, edoc)

    if edoc.status != "completed":
        messages.error(request, "Document is not yet complete.")
        return redirect("documents_tenant:edoc_detail", pk=pk)

    if not edoc.final_pdf:
        messages.error(request, "PDF not yet generated.")
        return redirect("documents_tenant:edoc_detail", pk=pk)

    from django.http import FileResponse
    return FileResponse(
        edoc.final_pdf.open("rb"),
        as_attachment=True,
        filename=f"{edoc.title}.pdf",
    )
