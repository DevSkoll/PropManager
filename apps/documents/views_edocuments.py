"""
Admin views for eDocument Creator and management.

Provides views for creating, editing, and managing eDocument templates
and document instances with the markdown editor.
"""

import json

import markdown
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.decorators import admin_required
from apps.leases.models import Lease
from apps.properties.models import Property

from .forms import EDocumentCreateForm, EDocumentSendForm, EDocumentTemplateForm
from .markdown_parser import (
    extract_required_roles,
    parse_signature_tags,
    replace_tags_with_html,
    validate_document,
)
from .models import (
    EDocument,
    EDocumentSignatureBlock,
    EDocumentSigner,
    EDocumentTemplate,
)
from .variables import (
    TemplateVariableResolver,
    get_available_variables,
    get_sample_variables,
)


# =============================================================================
# Template Views
# =============================================================================


@admin_required
def admin_template_list(request):
    """List all eDocument templates."""
    templates = EDocumentTemplate.objects.select_related("property").order_by("-created_at")

    # Filters
    template_type = request.GET.get("type")
    if template_type:
        templates = templates.filter(template_type=template_type)

    is_active = request.GET.get("active")
    if is_active == "1":
        templates = templates.filter(is_active=True)
    elif is_active == "0":
        templates = templates.filter(is_active=False)

    context = {
        "templates": templates,
        "template_types": EDocumentTemplate.TEMPLATE_TYPE_CHOICES,
        "current_type": template_type,
        "current_active": is_active,
    }
    return render(request, "documents/admin_template_list.html", context)


@admin_required
def admin_template_create(request):
    """Create a new eDocument template with markdown editor."""
    if request.method == "POST":
        form = EDocumentTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            messages.success(request, f"Template '{template.name}' created successfully.")
            return redirect("documents_admin:template_detail", pk=template.pk)
    else:
        form = EDocumentTemplateForm()

    context = {
        "form": form,
        "available_variables": get_available_variables(),
        "sample_variables": json.dumps(get_sample_variables()),
        "is_edit": False,
    }
    return render(request, "documents/admin_template_form.html", context)


@admin_required
def admin_template_detail(request, pk):
    """View template details."""
    template = get_object_or_404(EDocumentTemplate, pk=pk)

    # Parse signature tags from content
    parsed = parse_signature_tags(template.content)

    # Render preview with sample variables
    sample_vars = get_sample_variables()
    resolver = TemplateVariableResolver(extra_variables=sample_vars)
    preview_content = resolver.substitute(template.content)
    preview_html = markdown.markdown(preview_content, extensions=["tables", "fenced_code"])

    # Replace signature tags with placeholder HTML
    preview_html = replace_tags_with_html(preview_html)

    context = {
        "template": template,
        "parsed_tags": parsed,
        "preview_html": preview_html,
        "document_count": template.documents.count(),
    }
    return render(request, "documents/admin_template_detail.html", context)


@admin_required
def admin_template_edit(request, pk):
    """Edit an existing template."""
    template = get_object_or_404(EDocumentTemplate, pk=pk)

    if request.method == "POST":
        form = EDocumentTemplateForm(request.POST, instance=template)
        if form.is_valid():
            template = form.save(commit=False)
            template.updated_by = request.user
            template.save()
            messages.success(request, f"Template '{template.name}' updated successfully.")
            return redirect("documents_admin:template_detail", pk=template.pk)
    else:
        form = EDocumentTemplateForm(instance=template)

    context = {
        "form": form,
        "template": template,
        "available_variables": get_available_variables(),
        "sample_variables": json.dumps(get_sample_variables()),
        "is_edit": True,
    }
    return render(request, "documents/admin_template_form.html", context)


@admin_required
@require_POST
def admin_template_delete(request, pk):
    """Delete a template (soft delete by marking inactive)."""
    template = get_object_or_404(EDocumentTemplate, pk=pk)

    # Check if template has been used
    if template.documents.exists():
        template.is_active = False
        template.save(update_fields=["is_active"])
        messages.warning(
            request,
            f"Template '{template.name}' has been archived (has associated documents)."
        )
    else:
        template.delete()
        messages.success(request, f"Template '{template.name}' deleted.")

    return redirect("documents_admin:template_list")


@admin_required
def admin_template_preview(request, pk):
    """AJAX endpoint for live preview of template."""
    template = get_object_or_404(EDocumentTemplate, pk=pk)

    # Get lease context if provided
    lease_id = request.GET.get("lease")
    if lease_id:
        try:
            lease = Lease.objects.select_related("tenant", "unit__property").get(pk=lease_id)
            resolver = TemplateVariableResolver(
                lease=lease,
                landlord_user=request.user,
            )
        except Lease.DoesNotExist:
            resolver = TemplateVariableResolver(extra_variables=get_sample_variables())
    else:
        resolver = TemplateVariableResolver(extra_variables=get_sample_variables())

    # Substitute variables
    content = resolver.substitute(template.content)

    # Convert to HTML
    html = markdown.markdown(content, extensions=["tables", "fenced_code"])

    # Replace signature tags with placeholders
    html = replace_tags_with_html(html)

    return JsonResponse({"html": html})


# =============================================================================
# eDocument Views
# =============================================================================


@admin_required
def admin_edoc_list(request):
    """List all eDocuments."""
    edocs = EDocument.objects.select_related(
        "template", "lease", "tenant", "edoc_property"
    ).order_by("-created_at")

    # Filters
    status = request.GET.get("status")
    if status:
        edocs = edocs.filter(status=status)

    context = {
        "edocs": edocs,
        "status_choices": EDocument.STATUS_CHOICES,
        "current_status": status,
    }
    return render(request, "documents/admin_edoc_list.html", context)


@admin_required
def admin_edoc_create(request):
    """Create a new eDocument (from template or scratch)."""
    template_id = request.GET.get("template")
    template = None
    initial_content = ""

    if template_id:
        template = get_object_or_404(EDocumentTemplate, pk=template_id, is_active=True)
        initial_content = template.content

    if request.method == "POST":
        form = EDocumentCreateForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                edoc = form.save(commit=False)
                edoc.template = template
                edoc.created_by = request.user

                # Validate content
                is_valid, errors = validate_document(edoc.content)
                if not is_valid:
                    for error in errors:
                        form.add_error("content", error)
                else:
                    edoc.save()

                    # Create signature blocks from parsed tags
                    _create_signature_blocks(edoc)

                    messages.success(request, f"Document '{edoc.title}' created.")
                    return redirect("documents_admin:edoc_detail", pk=edoc.pk)
    else:
        initial = {}
        if template:
            initial["title"] = template.name
            initial["content"] = initial_content
        form = EDocumentCreateForm(initial=initial)

    # Get available templates and leases for the form
    templates = EDocumentTemplate.objects.filter(is_active=True).order_by("name")
    leases = Lease.objects.filter(status="active").select_related("tenant", "unit__property")

    context = {
        "form": form,
        "selected_template": template,
        "templates": templates,
        "leases": leases,
        "available_variables": get_available_variables(),
        "sample_variables": json.dumps(get_sample_variables()),
    }
    return render(request, "documents/admin_edoc_create.html", context)


@admin_required
def admin_edoc_detail(request, pk):
    """View eDocument details with signing progress."""
    edoc = get_object_or_404(
        EDocument.objects.select_related("template", "lease", "tenant", "edoc_property"),
        pk=pk
    )

    signers = edoc.signers.all()
    blocks = edoc.signature_blocks.select_related("signer").all()

    # Render content with variables
    if edoc.lease:
        resolver = TemplateVariableResolver(
            lease=edoc.lease,
            landlord_user=request.user,
        )
        rendered_content = resolver.substitute(edoc.content)
    else:
        rendered_content = edoc.content

    # Convert to HTML
    rendered_html = markdown.markdown(rendered_content, extensions=["tables", "fenced_code"])

    # Get signed blocks for display
    signed_blocks = {
        block.block_order: block.image
        for block in blocks if block.is_signed
    }
    rendered_html = replace_tags_with_html(rendered_html, signed_blocks=signed_blocks)

    context = {
        "edoc": edoc,
        "signers": signers,
        "blocks": blocks,
        "rendered_html": rendered_html,
        "progress": edoc.signature_progress,
    }
    return render(request, "documents/admin_edoc_detail.html", context)


@admin_required
def admin_edoc_edit(request, pk):
    """Edit eDocument (only if in draft status)."""
    edoc = get_object_or_404(EDocument, pk=pk)

    if edoc.status != "draft":
        messages.error(request, "Cannot edit a document that has been sent for signing.")
        return redirect("documents_admin:edoc_detail", pk=pk)

    if request.method == "POST":
        form = EDocumentCreateForm(request.POST, instance=edoc)
        if form.is_valid():
            with transaction.atomic():
                edoc = form.save(commit=False)
                edoc.updated_by = request.user

                # Validate and recreate signature blocks
                is_valid, errors = validate_document(edoc.content)
                if not is_valid:
                    for error in errors:
                        form.add_error("content", error)
                else:
                    edoc.save()

                    # Recreate signature blocks
                    edoc.signature_blocks.all().delete()
                    edoc.signers.all().delete()
                    _create_signature_blocks(edoc)

                    messages.success(request, "Document updated.")
                    return redirect("documents_admin:edoc_detail", pk=pk)
    else:
        form = EDocumentCreateForm(instance=edoc)

    context = {
        "form": form,
        "edoc": edoc,
        "available_variables": get_available_variables(),
        "sample_variables": json.dumps(get_sample_variables()),
    }
    return render(request, "documents/admin_edoc_edit.html", context)


@admin_required
def admin_edoc_assign_signers(request, pk):
    """Assign users to signer roles."""
    edoc = get_object_or_404(EDocument, pk=pk)

    if edoc.status not in ("draft", "pending"):
        messages.error(request, "Cannot modify signers for this document.")
        return redirect("documents_admin:edoc_detail", pk=pk)

    # Get required roles from content
    required_roles = extract_required_roles(edoc.content)

    if request.method == "POST":
        form = EDocumentSendForm(request.POST, edoc=edoc, required_roles=required_roles)
        if form.is_valid():
            with transaction.atomic():
                # Update or create signers
                for role in required_roles:
                    user_field = f"signer_{role}"
                    name_field = f"name_{role}"
                    email_field = f"email_{role}"

                    user = form.cleaned_data.get(user_field)
                    name = form.cleaned_data.get(name_field, "")
                    email = form.cleaned_data.get(email_field, "")

                    # Get or create signer
                    signer, created = EDocumentSigner.objects.update_or_create(
                        document=edoc,
                        role=role,
                        defaults={
                            "user": user,
                            "name": name or (user.get_full_name() if user else role.title()),
                            "email": email or (user.email if user else ""),
                        }
                    )

                    # Ensure signature blocks exist for this signer
                    _ensure_signer_blocks(edoc, signer)

                messages.success(request, "Signers assigned successfully.")
                return redirect("documents_admin:edoc_detail", pk=pk)
    else:
        # Pre-populate form with existing signers
        initial = {}
        for signer in edoc.signers.all():
            initial[f"signer_{signer.role}"] = signer.user
            initial[f"name_{signer.role}"] = signer.name
            initial[f"email_{signer.role}"] = signer.email

        # Auto-populate tenant from lease
        if edoc.lease and "tenant" in required_roles and "signer_tenant" not in initial:
            initial["signer_tenant"] = edoc.lease.tenant
            initial["name_tenant"] = edoc.lease.tenant.get_full_name()
            initial["email_tenant"] = edoc.lease.tenant.email

        form = EDocumentSendForm(initial=initial, edoc=edoc, required_roles=required_roles)

    context = {
        "edoc": edoc,
        "form": form,
        "required_roles": required_roles,
    }
    return render(request, "documents/admin_edoc_assign_signers.html", context)


@admin_required
@require_POST
def admin_edoc_send(request, pk):
    """Send document for signing."""
    edoc = get_object_or_404(EDocument, pk=pk)

    if edoc.status not in ("draft",):
        messages.error(request, "Document has already been sent.")
        return redirect("documents_admin:edoc_detail", pk=pk)

    # Verify all signers are assigned
    required_roles = extract_required_roles(edoc.content)
    assigned_roles = set(edoc.signers.values_list("role", flat=True))

    missing = set(required_roles) - assigned_roles
    if missing:
        messages.error(request, f"Missing signers for roles: {', '.join(missing)}")
        return redirect("documents_admin:edoc_assign_signers", pk=pk)

    # Verify all signers have email
    signers_without_email = edoc.signers.filter(email="")
    if signers_without_email.exists():
        messages.error(request, "All signers must have an email address.")
        return redirect("documents_admin:edoc_assign_signers", pk=pk)

    # Update status
    edoc.status = "pending"
    edoc.sent_at = timezone.now()
    edoc.save(update_fields=["status", "sent_at"])

    # TODO: Send notification emails to signers
    # _send_signing_notifications(edoc)

    messages.success(request, f"Document sent to {edoc.signers.count()} signer(s).")
    return redirect("documents_admin:edoc_detail", pk=pk)


@admin_required
@require_POST
def admin_edoc_cancel(request, pk):
    """Cancel a document."""
    edoc = get_object_or_404(EDocument, pk=pk)

    if edoc.status == "completed":
        messages.error(request, "Cannot cancel a completed document.")
        return redirect("documents_admin:edoc_detail", pk=pk)

    edoc.status = "cancelled"
    edoc.save(update_fields=["status"])

    messages.success(request, "Document cancelled.")
    return redirect("documents_admin:edoc_detail", pk=pk)


@admin_required
def admin_edoc_pdf(request, pk):
    """Download PDF of signed document."""
    edoc = get_object_or_404(EDocument, pk=pk)

    if edoc.final_pdf:
        # Serve existing PDF
        response = HttpResponse(edoc.final_pdf.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{edoc.title}.pdf"'
        return response

    # TODO: Generate PDF on the fly if not yet generated
    messages.error(request, "PDF not yet available. Document signing may not be complete.")
    return redirect("documents_admin:edoc_detail", pk=pk)


@admin_required
def admin_edoc_sign_as_landlord(request, pk):
    """Allow admin to sign the document as landlord."""
    edoc = get_object_or_404(EDocument, pk=pk)

    # Find landlord signer
    try:
        signer = edoc.signers.get(role="landlord")
    except EDocumentSigner.DoesNotExist:
        messages.error(request, "No landlord signature required for this document.")
        return redirect("documents_admin:edoc_detail", pk=pk)

    if signer.is_signed:
        messages.info(request, "Landlord signature already captured.")
        return redirect("documents_admin:edoc_detail", pk=pk)

    if request.method == "POST":
        signature_data = request.POST.get("signature_data")
        if signature_data:
            with transaction.atomic():
                # Update signer
                signer.signature_image = signature_data
                signer.signed_at = timezone.now()
                signer.ip_address = _get_client_ip(request)
                signer.user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
                signer.user = request.user
                signer.save()

                # Update all signature blocks for this signer
                signer.blocks.update(
                    image=signature_data,
                    signed_at=timezone.now(),
                    ip_address=signer.ip_address,
                )

                # Check if document is complete
                if edoc.is_fully_signed:
                    edoc.check_completion()
                    messages.success(request, "Document fully signed and completed!")
                else:
                    if edoc.status == "pending":
                        edoc.status = "partial"
                        edoc.save(update_fields=["status"])
                    messages.success(request, "Signature captured.")

                return redirect("documents_admin:edoc_detail", pk=pk)
        else:
            messages.error(request, "Please draw your signature.")

    # Get blocks for landlord
    blocks = signer.blocks.all()

    # Render document content
    if edoc.lease:
        resolver = TemplateVariableResolver(lease=edoc.lease, landlord_user=request.user)
        rendered_content = resolver.substitute(edoc.content)
    else:
        rendered_content = edoc.content

    rendered_html = markdown.markdown(rendered_content, extensions=["tables", "fenced_code"])

    context = {
        "edoc": edoc,
        "signer": signer,
        "blocks": blocks,
        "rendered_html": rendered_html,
    }
    return render(request, "documents/admin_edoc_sign.html", context)


# =============================================================================
# Helper Functions
# =============================================================================


def _create_signature_blocks(edoc: EDocument) -> None:
    """Create signature blocks from parsed content."""
    parsed = parse_signature_tags(edoc.content)

    # Group tags by role
    role_tags = {}
    for tag in parsed.tags:
        if tag.role not in role_tags:
            role_tags[tag.role] = []
        role_tags[tag.role].append(tag)

    # Create signers and blocks
    for role, tags in role_tags.items():
        # Create or get signer placeholder
        signer, _ = EDocumentSigner.objects.get_or_create(
            document=edoc,
            role=role,
            defaults={
                "name": role.title(),
                "email": "",
            }
        )

        # Create signature blocks
        for tag in tags:
            EDocumentSignatureBlock.objects.create(
                document=edoc,
                signer=signer,
                block_type=tag.tag_type,
                block_order=tag.order,
            )


def _ensure_signer_blocks(edoc: EDocument, signer: EDocumentSigner) -> None:
    """Ensure signature blocks exist for a signer."""
    parsed = parse_signature_tags(edoc.content)

    for tag in parsed.tags:
        if tag.role == signer.role:
            EDocumentSignatureBlock.objects.get_or_create(
                document=edoc,
                signer=signer,
                block_order=tag.order,
                defaults={
                    "block_type": tag.tag_type,
                }
            )


def _get_client_ip(request) -> str:
    """Get client IP address from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
