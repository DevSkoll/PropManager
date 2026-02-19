from datetime import timedelta

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.models import ContractorAccessToken
from apps.core.decorators import admin_required, contractor_token_required, tenant_required
from apps.leases.models import Lease

from .forms import (
    ContractorAssignForm,
    ContractorStatusForm,
    TenantWorkOrderForm,
    WorkOrderAttachmentForm,
    WorkOrderForm,
    WorkOrderNoteForm,
    WorkOrderStatusForm,
)
from .models import ContractorAssignment, WorkOrder, WorkOrderAttachment, WorkOrderNote


# ---------------------------------------------------------------------------
# Admin views
# ---------------------------------------------------------------------------


@admin_required
def admin_workorder_list(request):
    qs = WorkOrder.objects.select_related("unit", "unit__property", "reported_by").all()

    status_filter = request.GET.get("status", "")
    priority_filter = request.GET.get("priority", "")

    if status_filter:
        qs = qs.filter(status=status_filter)
    if priority_filter:
        qs = qs.filter(priority=priority_filter)

    context = {
        "workorders": qs,
        "status_choices": WorkOrder.STATUS_CHOICES,
        "priority_choices": WorkOrder.PRIORITY_CHOICES,
        "current_status": status_filter,
        "current_priority": priority_filter,
    }
    return render(request, "workorders/admin_workorder_list.html", context)


@admin_required
def admin_workorder_detail(request, pk):
    workorder = get_object_or_404(
        WorkOrder.objects.select_related("unit", "unit__property", "reported_by"),
        pk=pk,
    )
    notes = workorder.notes.select_related("author_user", "author_contractor_token").all()
    attachments = workorder.attachments.all()
    assignment = workorder.assignments.select_related("access_token").first()

    note_form = WorkOrderNoteForm()
    attachment_form = WorkOrderAttachmentForm()
    status_form = WorkOrderStatusForm(initial={"new_status": workorder.status})

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "add_note":
            note_form = WorkOrderNoteForm(request.POST)
            if note_form.is_valid():
                note = note_form.save(commit=False)
                note.work_order = workorder
                note.author_user = request.user
                note.save()
                messages.success(request, "Note added successfully.")
                return redirect("workorders_admin:workorder_detail", pk=workorder.pk)

        elif action == "upload_file":
            attachment_form = WorkOrderAttachmentForm(request.POST, request.FILES)
            if attachment_form.is_valid():
                attachment = attachment_form.save(commit=False)
                attachment.work_order = workorder
                attachment.uploaded_by_user = request.user
                attachment.save()
                messages.success(request, "File uploaded successfully.")
                return redirect("workorders_admin:workorder_detail", pk=workorder.pk)

    context = {
        "workorder": workorder,
        "notes": notes,
        "attachments": attachments,
        "assignment": assignment,
        "note_form": note_form,
        "attachment_form": attachment_form,
        "status_form": status_form,
    }
    return render(request, "workorders/admin_workorder_detail.html", context)


@admin_required
def admin_workorder_create(request):
    if request.method == "POST":
        form = WorkOrderForm(request.POST)
        if form.is_valid():
            workorder = form.save(commit=False)
            workorder.reported_by = request.user
            workorder.created_by = request.user
            workorder.save()
            messages.success(request, "Work order created successfully.")
            return redirect("workorders_admin:workorder_detail", pk=workorder.pk)
    else:
        form = WorkOrderForm()

    return render(request, "workorders/admin_workorder_create.html", {"form": form})


@admin_required
def admin_workorder_update_status(request, pk):
    workorder = get_object_or_404(WorkOrder, pk=pk)

    if request.method == "POST":
        form = WorkOrderStatusForm(request.POST)
        if form.is_valid():
            new_status = form.cleaned_data["new_status"]
            if workorder.can_transition_to(new_status):
                workorder.status = new_status
                workorder.updated_by = request.user
                if new_status == "completed":
                    workorder.completed_date = timezone.now().date()
                workorder.save()
                messages.success(
                    request,
                    f"Status updated to {workorder.get_status_display()}.",
                )
            else:
                messages.error(
                    request,
                    f"Cannot transition from {workorder.get_status_display()} to {dict(WorkOrder.STATUS_CHOICES).get(new_status, new_status)}.",
                )
        else:
            messages.error(request, "Invalid status selected.")

    return redirect("workorders_admin:workorder_detail", pk=workorder.pk)


@admin_required
def admin_workorder_assign(request, pk):
    workorder = get_object_or_404(WorkOrder, pk=pk)

    if request.method == "POST":
        form = ContractorAssignForm(request.POST)
        if form.is_valid():
            expiry_days = form.cleaned_data["expiry_days"]

            # Create the access token
            token = ContractorAccessToken(
                contractor_name=form.cleaned_data["contractor_name"],
                contractor_phone=form.cleaned_data.get("phone", ""),
                contractor_email=form.cleaned_data.get("email", ""),
                work_order=workorder,
                expires_at=timezone.now() + timedelta(days=expiry_days),
            )
            token.save()

            # Create the assignment
            ContractorAssignment.objects.create(
                work_order=workorder,
                contractor_name=form.cleaned_data["contractor_name"],
                contractor_phone=form.cleaned_data.get("phone", ""),
                contractor_email=form.cleaned_data.get("email", ""),
                access_token=token,
                notes=form.cleaned_data.get("notes", ""),
            )

            # Transition status to assigned if possible
            if workorder.can_transition_to("assigned"):
                workorder.status = "assigned"
                workorder.updated_by = request.user
                workorder.save()

            token_link = request.build_absolute_uri(f"/contractor/{token.token}/")
            messages.success(
                request,
                f"Contractor assigned. Access link: {token_link}",
            )
            return redirect("workorders_admin:workorder_detail", pk=workorder.pk)
    else:
        form = ContractorAssignForm()

    context = {
        "workorder": workorder,
        "form": form,
    }
    return render(request, "workorders/admin_workorder_assign.html", context)


# ---------------------------------------------------------------------------
# Tenant views
# ---------------------------------------------------------------------------


@tenant_required
def tenant_workorder_list(request):
    # Get units from tenant's active leases
    active_leases = Lease.objects.filter(
        tenant=request.user,
        status="active",
    )
    tenant_unit_ids = active_leases.values_list("unit_id", flat=True)

    qs = WorkOrder.objects.select_related("unit", "unit__property").filter(
        Q(reported_by=request.user) | Q(unit_id__in=tenant_unit_ids)
    ).distinct()

    context = {
        "workorders": qs,
    }
    return render(request, "workorders/tenant_workorder_list.html", context)


@tenant_required
def tenant_workorder_create(request):
    # Pre-fill unit from active lease
    active_lease = Lease.objects.filter(
        tenant=request.user,
        status="active",
    ).select_related("unit", "unit__property").first()

    if request.method == "POST":
        form = TenantWorkOrderForm(request.POST)
        if form.is_valid():
            workorder = form.save(commit=False)
            if active_lease:
                workorder.unit = active_lease.unit
            workorder.reported_by = request.user
            workorder.created_by = request.user
            workorder.save()
            messages.success(request, "Work order submitted successfully.")
            return redirect("workorders_tenant:workorder_detail", pk=workorder.pk)
    else:
        form = TenantWorkOrderForm()

    context = {
        "form": form,
        "active_lease": active_lease,
    }
    return render(request, "workorders/tenant_workorder_create.html", context)


@tenant_required
def tenant_workorder_detail(request, pk):
    active_leases = Lease.objects.filter(
        tenant=request.user,
        status="active",
    )
    tenant_unit_ids = active_leases.values_list("unit_id", flat=True)

    workorder = get_object_or_404(
        WorkOrder.objects.select_related("unit", "unit__property"),
        Q(reported_by=request.user) | Q(unit_id__in=tenant_unit_ids),
        pk=pk,
    )

    # Non-internal notes only
    notes = workorder.notes.select_related(
        "author_user", "author_contractor_token"
    ).filter(is_internal=False)

    attachments = workorder.attachments.all()
    note_form = WorkOrderNoteForm(initial={"is_internal": False})

    context = {
        "workorder": workorder,
        "notes": notes,
        "attachments": attachments,
        "note_form": note_form,
    }
    return render(request, "workorders/tenant_workorder_detail.html", context)


@tenant_required
def tenant_workorder_add_note(request, pk):
    active_leases = Lease.objects.filter(
        tenant=request.user,
        status="active",
    )
    tenant_unit_ids = active_leases.values_list("unit_id", flat=True)

    workorder = get_object_or_404(
        WorkOrder,
        Q(reported_by=request.user) | Q(unit_id__in=tenant_unit_ids),
        pk=pk,
    )

    if request.method == "POST":
        form = WorkOrderNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.work_order = workorder
            note.author_user = request.user
            note.is_internal = False  # Tenants cannot create internal notes
            note.save()
            messages.success(request, "Note added successfully.")

    return redirect("workorders_tenant:workorder_detail", pk=workorder.pk)


# ---------------------------------------------------------------------------
# Contractor views
# ---------------------------------------------------------------------------


@contractor_token_required
def contractor_workorder_detail(request, token):
    access_token = request.contractor_token
    workorder = access_token.work_order

    # Prefetch related data
    workorder = WorkOrder.objects.select_related(
        "unit", "unit__property"
    ).get(pk=workorder.pk)

    notes = workorder.notes.select_related(
        "author_user", "author_contractor_token"
    ).filter(is_internal=False)
    attachments = workorder.attachments.all()
    status_form = ContractorStatusForm(initial={"new_status": workorder.status})
    note_form = WorkOrderNoteForm(initial={"is_internal": False})
    attachment_form = WorkOrderAttachmentForm()

    context = {
        "workorder": workorder,
        "notes": notes,
        "attachments": attachments,
        "status_form": status_form,
        "note_form": note_form,
        "attachment_form": attachment_form,
        "access_token": access_token,
        "token": token,
    }
    return render(request, "workorders/contractor_workorder_detail.html", context)


@contractor_token_required
def contractor_update_status(request, token):
    access_token = request.contractor_token
    workorder = access_token.work_order

    if request.method == "POST":
        form = ContractorStatusForm(request.POST)
        if form.is_valid():
            new_status = form.cleaned_data["new_status"]
            if workorder.can_transition_to(new_status):
                workorder.status = new_status
                if new_status == "completed":
                    workorder.completed_date = timezone.now().date()
                workorder.save()
                messages.success(
                    request,
                    f"Status updated to {workorder.get_status_display()}.",
                )
            else:
                messages.error(
                    request,
                    f"Cannot transition from {workorder.get_status_display()} to {dict(WorkOrder.STATUS_CHOICES).get(new_status, new_status)}.",
                )
        else:
            messages.error(request, "Invalid status selected.")

    return redirect("workorders_contractor:workorder_detail", token=token)


@contractor_token_required
def contractor_add_note(request, token):
    access_token = request.contractor_token
    workorder = access_token.work_order

    if request.method == "POST":
        form = WorkOrderNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.work_order = workorder
            note.author_contractor_token = access_token
            note.is_internal = False
            note.save()
            messages.success(request, "Note added successfully.")

    return redirect("workorders_contractor:workorder_detail", token=token)


@contractor_token_required
def contractor_upload_image(request, token):
    access_token = request.contractor_token
    workorder = access_token.work_order

    if request.method == "POST":
        form = WorkOrderAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.work_order = workorder
            attachment.uploaded_by_contractor_token = access_token
            attachment.save()
            messages.success(request, "File uploaded successfully.")
        else:
            messages.error(request, "Failed to upload file. Only images and PDFs are allowed.")

    return redirect("workorders_contractor:workorder_detail", token=token)
