"""
Admin views for managing tenant onboarding.

Provides views for:
- Onboarding template management (CRUD)
- Onboarding session management (create, view, resend, cancel)
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.core.decorators import admin_required
from apps.documents.models import EDocumentTemplate
from apps.properties.models import Property, Unit

from .forms import (
    OnboardingSessionCreateForm,
    OnboardingTemplateDocumentForm,
    OnboardingTemplateFeeForm,
    OnboardingTemplateForm,
    StepConfigForm,
)
from .models import (
    OnboardingDocument,
    OnboardingPayment,
    OnboardingPreset,
    OnboardingSession,
    OnboardingTemplate,
    OnboardingTemplateDocument,
    OnboardingTemplateFee,
)
from .services import OnboardingService


# =============================================================================
# Preset Management
# =============================================================================


@login_required
@admin_required
def preset_list(request):
    """List all onboarding presets."""
    presets = OnboardingPreset.objects.filter(is_active=True).order_by("category", "name")

    # Group by category
    categories = {}
    for preset in presets:
        cat = preset.category
        if cat not in categories:
            categories[cat] = {
                "name": preset.get_category_display(),
                "presets": [],
            }
        categories[cat]["presets"].append(preset)

    context = {
        "presets": presets,
        "categories": categories,
    }
    return render(request, "tenant_lifecycle/admin/preset_list.html", context)


@login_required
@admin_required
def preset_detail(request, pk):
    """View preset details."""
    preset = get_object_or_404(OnboardingPreset, pk=pk)

    context = {
        "preset": preset,
        "enabled_steps": [
            {"name": name, **config}
            for name, config in sorted(
                preset.steps_config.items(),
                key=lambda x: x[1].get("order", 99)
            )
            if config.get("enabled", True)
        ],
    }
    return render(request, "tenant_lifecycle/admin/preset_detail.html", context)


@login_required
@admin_required
def preset_apply(request, pk):
    """Apply a preset to create a new template for a property."""
    preset = get_object_or_404(OnboardingPreset, pk=pk)

    if request.method == "POST":
        property_id = request.POST.get("property")
        name = request.POST.get("name", preset.name)
        is_default = request.POST.get("is_default") == "on"

        if not property_id:
            messages.error(request, "Please select a property.")
            return redirect("tenant_lifecycle_admin:admin_preset_apply", pk=pk)

        prop = get_object_or_404(Property, pk=property_id)

        # Create template from preset
        template = preset.create_template_for_property(
            prop=prop,
            name=name,
            is_default=is_default,
        )

        messages.success(
            request,
            f"Template '{template.name}' created for {prop.name} from preset '{preset.name}'."
        )
        return redirect("tenant_lifecycle_admin:admin_template_detail", pk=template.pk)

    properties = Property.objects.all()

    context = {
        "preset": preset,
        "properties": properties,
    }
    return render(request, "tenant_lifecycle/admin/preset_apply.html", context)


# =============================================================================
# Template Management
# =============================================================================


@login_required
@admin_required
def template_list(request):
    """List all onboarding templates."""
    templates = OnboardingTemplate.objects.select_related("property").annotate(
        session_count=Count("sessions"),
        active_session_count=Count(
            "sessions",
            filter=Q(sessions__status__in=["invited", "started", "in_progress"])
        ),
    ).order_by("property__name", "name")

    # Filter by property if specified
    property_id = request.GET.get("property")
    if property_id:
        templates = templates.filter(property_id=property_id)

    properties = Property.objects.all()

    context = {
        "templates": templates,
        "properties": properties,
        "selected_property": property_id,
    }
    return render(request, "tenant_lifecycle/admin/template_list.html", context)


@login_required
@admin_required
def template_create(request):
    """Create a new onboarding template."""
    if request.method == "POST":
        form = OnboardingTemplateForm(request.POST)
        step_form = StepConfigForm(request.POST)

        if form.is_valid() and step_form.is_valid():
            template = form.save(commit=False)
            template.steps_config = step_form.get_steps_config()
            template.save()

            messages.success(request, f"Template '{template.name}' created successfully.")
            return redirect("tenant_lifecycle_admin:admin_template_detail", pk=template.pk)
    else:
        form = OnboardingTemplateForm()
        step_form = StepConfigForm(steps_config=OnboardingTemplate.get_default_steps_config())

    context = {
        "form": form,
        "step_form": step_form,
        "is_create": True,
    }
    return render(request, "tenant_lifecycle/admin/template_form.html", context)


@login_required
@admin_required
def template_detail(request, pk):
    """View onboarding template details."""
    template = get_object_or_404(
        OnboardingTemplate.objects.select_related("property"),
        pk=pk
    )

    documents = template.documents.select_related("edocument_template").all()
    fees = template.fees.all()

    # Get recent sessions using this template
    recent_sessions = OnboardingSession.objects.filter(
        template=template
    ).select_related("unit", "tenant").order_by("-created_at")[:10]

    context = {
        "template": template,
        "documents": documents,
        "fees": fees,
        "recent_sessions": recent_sessions,
        "enabled_steps": template.get_enabled_steps(),
    }
    return render(request, "tenant_lifecycle/admin/template_detail.html", context)


@login_required
@admin_required
def template_edit(request, pk):
    """Edit an onboarding template."""
    template = get_object_or_404(OnboardingTemplate, pk=pk)

    if request.method == "POST":
        form = OnboardingTemplateForm(request.POST, instance=template)
        step_form = StepConfigForm(request.POST, steps_config=template.steps_config)

        if form.is_valid() and step_form.is_valid():
            template = form.save(commit=False)
            template.steps_config = step_form.get_steps_config()
            template.save()

            messages.success(request, f"Template '{template.name}' updated successfully.")
            return redirect("tenant_lifecycle_admin:admin_template_detail", pk=template.pk)
    else:
        form = OnboardingTemplateForm(instance=template)
        step_form = StepConfigForm(steps_config=template.steps_config)

    context = {
        "form": form,
        "step_form": step_form,
        "template": template,
        "is_create": False,
    }
    return render(request, "tenant_lifecycle/admin/template_form.html", context)


@login_required
@admin_required
def template_documents(request, pk):
    """Manage documents for a template."""
    template = get_object_or_404(OnboardingTemplate, pk=pk)

    if request.method == "POST":
        form = OnboardingTemplateDocumentForm(request.POST)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.template = template
            doc.save()
            messages.success(request, "Document added to template.")
            return redirect("tenant_lifecycle_admin:admin_template_documents", pk=pk)
    else:
        form = OnboardingTemplateDocumentForm()

    # Get available document templates
    form.fields["edocument_template"].queryset = EDocumentTemplate.objects.filter(
        is_active=True
    )

    documents = template.documents.select_related("edocument_template").all()

    context = {
        "template": template,
        "documents": documents,
        "form": form,
    }
    return render(request, "tenant_lifecycle/admin/template_documents.html", context)


@login_required
@admin_required
@require_POST
def template_document_delete(request, pk, doc_pk):
    """Delete a document from a template."""
    template = get_object_or_404(OnboardingTemplate, pk=pk)
    doc = get_object_or_404(OnboardingTemplateDocument, pk=doc_pk, template=template)
    doc.delete()
    messages.success(request, "Document removed from template.")
    return redirect("tenant_lifecycle_admin:admin_template_documents", pk=pk)


@login_required
@admin_required
def template_fees(request, pk):
    """Manage fees for a template."""
    template = get_object_or_404(OnboardingTemplate, pk=pk)

    if request.method == "POST":
        form = OnboardingTemplateFeeForm(request.POST)
        if form.is_valid():
            fee = form.save(commit=False)
            fee.template = template
            fee.save()
            messages.success(request, "Fee added to template.")
            return redirect("tenant_lifecycle_admin:admin_template_fees", pk=pk)
    else:
        form = OnboardingTemplateFeeForm()

    fees = template.fees.all()

    context = {
        "template": template,
        "fees": fees,
        "form": form,
    }
    return render(request, "tenant_lifecycle/admin/template_fees.html", context)


@login_required
@admin_required
@require_POST
def template_fee_delete(request, pk, fee_pk):
    """Delete a fee from a template."""
    template = get_object_or_404(OnboardingTemplate, pk=pk)
    fee = get_object_or_404(OnboardingTemplateFee, pk=fee_pk, template=template)
    fee.delete()
    messages.success(request, "Fee removed from template.")
    return redirect("tenant_lifecycle_admin:admin_template_fees", pk=pk)


# =============================================================================
# Session Management
# =============================================================================


@login_required
@admin_required
def session_list(request):
    """List all onboarding sessions."""
    sessions = OnboardingSession.objects.select_related(
        "template", "unit", "tenant", "created_by"
    ).order_by("-created_at")

    # Filter by status
    status = request.GET.get("status")
    if status:
        sessions = sessions.filter(status=status)

    # Filter by property
    property_id = request.GET.get("property")
    if property_id:
        sessions = sessions.filter(unit__property_id=property_id)

    # Statistics
    stats = {
        "total": OnboardingSession.objects.count(),
        "invited": OnboardingSession.objects.filter(status="invited").count(),
        "in_progress": OnboardingSession.objects.filter(status__in=["started", "in_progress"]).count(),
        "completed": OnboardingSession.objects.filter(status="completed").count(),
        "expired": OnboardingSession.objects.filter(status="expired").count(),
    }

    properties = Property.objects.all()

    context = {
        "sessions": sessions[:100],  # Limit for performance
        "stats": stats,
        "properties": properties,
        "selected_status": status,
        "selected_property": property_id,
    }
    return render(request, "tenant_lifecycle/admin/session_list.html", context)


@login_required
@admin_required
def session_create(request):
    """
    Create a new onboarding session from a pending lease.

    The lease must have no tenant assigned and prospective tenant info.
    Unit and prospective info are pulled from the selected lease.
    """
    if request.method == "POST":
        form = OnboardingSessionCreateForm(request.POST)
        if form.is_valid():
            lease = form.cleaned_data["lease"]

            # Pull all info from the lease
            session = OnboardingService.create_session(
                unit=lease.unit,
                prospective_email=lease.prospective_email,
                prospective_first_name=lease.prospective_first_name,
                prospective_last_name=lease.prospective_last_name,
                prospective_phone=lease.prospective_phone,
                template=form.cleaned_data.get("template"),
                lease=lease,
                created_by=request.user,
                notes=form.cleaned_data.get("notes", ""),
                send_invitation=True,
            )
            messages.success(
                request,
                f"Onboarding invitation sent to {session.prospective_email}. "
                f"Session created for {lease.display_tenant_name}."
            )
            return redirect("tenant_lifecycle_admin:admin_session_detail", pk=session.pk)
    else:
        form = OnboardingSessionCreateForm()

        # Pre-populate if lease_id provided (from lease detail page)
        lease_id = request.GET.get("lease")
        if lease_id:
            form.fields["lease"].initial = lease_id

    # Filter templates to active ones
    form.fields["template"].queryset = OnboardingTemplate.objects.filter(is_active=True)

    # Get count of pending leases for context
    pending_count = form.fields["lease"].queryset.count()

    context = {
        "form": form,
        "pending_count": pending_count,
    }
    return render(request, "tenant_lifecycle/admin/session_create.html", context)


@login_required
@admin_required
def session_detail(request, pk):
    """View onboarding session details."""
    session = get_object_or_404(
        OnboardingSession.objects.select_related(
            "template", "unit", "lease", "tenant", "created_by"
        ),
        pk=pk
    )

    # Get session summary
    summary = OnboardingService.get_session_summary(session)

    # Get documents and payments
    documents = OnboardingDocument.objects.filter(session=session).select_related(
        "template_document", "edocument"
    )
    payments = OnboardingPayment.objects.filter(session=session)

    # Get step logs
    step_logs = session.step_logs.order_by("-started_at")[:20]

    context = {
        "session": session,
        "summary": summary,
        "documents": documents,
        "payments": payments,
        "step_logs": step_logs,
    }
    return render(request, "tenant_lifecycle/admin/session_detail.html", context)


@login_required
@admin_required
@require_POST
def session_resend_invite(request, pk):
    """Resend onboarding invitation."""
    session = get_object_or_404(OnboardingSession, pk=pk)

    if session.status in ("completed", "cancelled"):
        messages.error(request, "Cannot resend invitation for completed or cancelled sessions.")
        return redirect("tenant_lifecycle_admin:admin_session_detail", pk=pk)

    result = OnboardingService.send_invitation(session)

    if result.get("email_sent") or result.get("sms_sent"):
        messages.success(request, "Invitation resent successfully.")
    else:
        messages.error(request, "Failed to send invitation. Please check contact information.")

    return redirect("tenant_lifecycle_admin:admin_session_detail", pk=pk)


@login_required
@admin_required
@require_POST
def session_regenerate_link(request, pk):
    """Regenerate onboarding access token."""
    session = get_object_or_404(OnboardingSession, pk=pk)

    if session.status in ("completed", "cancelled"):
        messages.error(request, "Cannot regenerate link for completed or cancelled sessions.")
        return redirect("tenant_lifecycle_admin:admin_session_detail", pk=pk)

    session.regenerate_token()
    messages.success(request, "New onboarding link generated. Don't forget to send the invitation.")

    return redirect("tenant_lifecycle_admin:admin_session_detail", pk=pk)


@login_required
@admin_required
@require_POST
def session_cancel(request, pk):
    """Cancel an onboarding session."""
    session = get_object_or_404(OnboardingSession, pk=pk)

    if session.status == "completed":
        messages.error(request, "Cannot cancel a completed session.")
        return redirect("tenant_lifecycle_admin:admin_session_detail", pk=pk)

    session.status = "cancelled"
    session.save(update_fields=["status", "updated_at"])

    messages.success(request, "Onboarding session cancelled.")
    return redirect("tenant_lifecycle_admin:admin_session_list")


@login_required
@admin_required
@require_POST
def session_delete(request, pk):
    """Permanently delete a cancelled onboarding session."""
    session = get_object_or_404(OnboardingSession, pk=pk)

    if session.status != "cancelled":
        messages.error(request, "Only cancelled sessions can be deleted.")
        return redirect("tenant_lifecycle_admin:admin_session_detail", pk=pk)

    session.delete()
    messages.success(request, "Onboarding session deleted.")
    return redirect("tenant_lifecycle_admin:admin_session_list")


@login_required
@admin_required
def session_progress_json(request, pk):
    """Get session progress as JSON (for AJAX updates)."""
    session = get_object_or_404(OnboardingSession, pk=pk)
    summary = OnboardingService.get_session_summary(session)

    return JsonResponse({
        "status": session.status,
        "progress_percent": summary["progress_percent"],
        "current_step": session.current_step,
        "steps": summary["steps"],
    })
