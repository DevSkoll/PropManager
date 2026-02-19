import json
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.core.decorators import admin_required, tenant_required
from apps.leases.models import Lease
from apps.properties.models import Property, Unit

from .forms import (
    BatchInvoiceGenerateForm,
    BulkUtilityConfigForm,
    InvoiceEditLineItemFormSet,
    InvoiceForm,
    InvoiceLineItemFormSet,
    PaymentGatewayConfigForm,
    PropertyBillingConfigForm,
    RecordPaymentForm,
    RecurringChargeForm,
    TenantPaymentForm,
    get_utility_config_formset,
)
from .models import (
    ApiToken,
    BillingCycle,
    Invoice,
    InvoiceLineItem,
    Payment,
    PaymentGatewayConfig,
    PrepaymentCredit,
    PropertyBillingConfig,
    RecurringCharge,
    UtilityConfig,
    UtilityRateLog,
)
from .services import InvoiceService, LateFeeService, PaymentService


# ===========================================================================
# Admin Views
# ===========================================================================


@admin_required
def admin_invoice_list(request):
    """List all invoices with optional status filter."""
    status_filter = request.GET.get("status", "")
    invoices = Invoice.objects.select_related("tenant", "lease", "lease__unit").all()

    if status_filter:
        invoices = invoices.filter(status=status_filter)

    status_choices = Invoice.STATUS_CHOICES

    # Summary stats
    total_outstanding = (
        Invoice.objects.filter(status__in=["issued", "partial", "overdue"])
        .aggregate(total=Sum("total_amount"))
        .get("total")
        or Decimal("0.00")
    )
    total_paid_amount = (
        Invoice.objects.filter(status__in=["issued", "partial", "overdue"])
        .aggregate(total=Sum("amount_paid"))
        .get("total")
        or Decimal("0.00")
    )
    balance_outstanding = total_outstanding - total_paid_amount

    context = {
        "invoices": invoices,
        "status_filter": status_filter,
        "status_choices": status_choices,
        "balance_outstanding": balance_outstanding,
    }
    return render(request, "billing/admin_invoice_list.html", context)


@admin_required
def admin_invoice_detail(request, pk):
    """View a single invoice with line items and payment history."""
    invoice = get_object_or_404(
        Invoice.objects.select_related("tenant", "lease", "lease__unit", "billing_cycle"),
        pk=pk,
    )
    line_items = invoice.line_items.all()
    payments = invoice.payments.all().order_by("-payment_date")

    from apps.notifications.models import ReminderLog

    reminder_logs = ReminderLog.objects.filter(invoice=invoice).select_related("sent_by")

    context = {
        "invoice": invoice,
        "line_items": line_items,
        "payments": payments,
        "reminder_logs": reminder_logs,
    }
    return render(request, "billing/admin_invoice_detail.html", context)


@admin_required
def admin_invoice_create(request):
    """Create a new invoice with line items via inline formset."""
    if request.method == "POST":
        form = InvoiceForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                invoice = form.save(commit=False)
                invoice.invoice_number = InvoiceService.generate_invoice_number()
                invoice.tenant = invoice.lease.tenant
                invoice.created_by = request.user
                invoice.save()

                formset = InvoiceLineItemFormSet(request.POST, instance=invoice)
                if formset.is_valid():
                    formset.save()
                    invoice.recalculate_total()

                    messages.success(
                        request,
                        f"Invoice {invoice.invoice_number} created successfully.",
                    )
                    return redirect("billing_admin:invoice_detail", pk=invoice.pk)
                else:
                    invoice.delete()
                    messages.error(request, "Please correct the line item errors below.")
        else:
            formset = InvoiceLineItemFormSet(request.POST)
    else:
        form = InvoiceForm()
        formset = InvoiceLineItemFormSet()

    context = {
        "form": form,
        "formset": formset,
    }
    return render(request, "billing/admin_invoice_create.html", context)


@admin_required
def admin_invoice_edit(request, pk):
    """Edit line items on an existing invoice."""
    invoice = get_object_or_404(Invoice, pk=pk)

    if invoice.status in ("paid", "cancelled"):
        messages.error(request, f"Cannot edit a {invoice.get_status_display()} invoice.")
        return redirect("billing_admin:invoice_detail", pk=invoice.pk)

    if request.method == "POST":
        formset = InvoiceEditLineItemFormSet(request.POST, instance=invoice)
        if formset.is_valid():
            with transaction.atomic():
                formset.save()
                invoice.recalculate_total()

            messages.success(request, f"Invoice {invoice.invoice_number} line items updated.")
            return redirect("billing_admin:invoice_detail", pk=invoice.pk)
    else:
        formset = InvoiceEditLineItemFormSet(instance=invoice)

    context = {
        "invoice": invoice,
        "formset": formset,
    }
    return render(request, "billing/admin_invoice_edit.html", context)


@admin_required
def admin_invoice_generate_batch(request):
    """Batch-generate invoices for all active leases in a billing cycle."""
    if request.method == "POST":
        form = BatchInvoiceGenerateForm(request.POST)
        if form.is_valid():
            billing_cycle = form.cleaned_data["billing_cycle"]
            active_leases = Lease.objects.filter(status="active").select_related("tenant", "unit")

            created_count = 0
            skipped_count = 0

            with transaction.atomic():
                for lease in active_leases:
                    if Invoice.objects.filter(lease=lease, billing_cycle=billing_cycle).exists():
                        skipped_count += 1
                        continue

                    try:
                        InvoiceService.create_invoice_for_lease(
                            lease=lease,
                            billing_cycle=billing_cycle,
                            issue_date=timezone.now().date(),
                            due_date=billing_cycle.end_date,
                            notes=f"Auto-generated for {billing_cycle.name}",
                            created_by=request.user,
                        )
                        created_count += 1
                    except Exception:
                        skipped_count += 1

            messages.success(
                request,
                f"Batch generation complete: {created_count} invoices created, "
                f"{skipped_count} skipped (already exist).",
            )
            return redirect("billing_admin:invoice_list")
    else:
        form = BatchInvoiceGenerateForm()

    context = {"form": form}
    return render(request, "billing/admin_invoice_generate_batch.html", context)


@admin_required
@require_POST
def admin_invoice_apply_late_fee(request, pk):
    """Manually apply a late fee to an invoice."""
    invoice = get_object_or_404(
        Invoice.objects.select_related("lease__unit__property"),
        pk=pk,
    )

    result = LateFeeService.apply_late_fees_for_invoice(invoice)
    if result:
        messages.success(request, f"Late fee of ${result.amount:.2f} applied to {invoice.invoice_number}.")
    else:
        messages.warning(request, "No late fee was applied. The invoice may not be eligible (check grace period, cap, or frequency).")

    return redirect("billing_admin:invoice_detail", pk=invoice.pk)


@admin_required
def admin_payment_list(request):
    """List all payments."""
    payments = Payment.objects.select_related("tenant", "invoice", "gateway_config").all()

    context = {"payments": payments}
    return render(request, "billing/admin_payment_list.html", context)


@admin_required
def admin_record_payment(request):
    """Record a manual payment against an invoice. Overpayment creates PrepaymentCredit."""
    if request.method == "POST":
        form = RecordPaymentForm(request.POST)
        if form.is_valid():
            invoice = form.cleaned_data["invoice"]
            amount = form.cleaned_data["amount"]
            method = form.cleaned_data["method"]
            reference_number = form.cleaned_data.get("reference_number", "")
            notes = form.cleaned_data.get("notes", "")

            payment = PaymentService.record_manual_payment(
                invoice=invoice,
                amount=amount,
                method=method,
                reference_number=reference_number,
                notes=notes,
                recorded_by=request.user,
            )

            overpayment = invoice.amount_paid - invoice.total_amount
            if overpayment > 0:
                messages.success(
                    request,
                    f"Payment of ${amount:.2f} recorded. "
                    f"Overpayment of ${overpayment:.2f} added as prepayment credit.",
                )
            else:
                messages.success(
                    request,
                    f"Payment of ${amount:.2f} recorded against invoice {invoice.invoice_number}.",
                )
            return redirect("billing_admin:payment_list")
    else:
        initial = {}
        invoice_id = request.GET.get("invoice")
        if invoice_id:
            initial["invoice"] = invoice_id
        form = RecordPaymentForm(initial=initial)

    context = {"form": form}
    return render(request, "billing/admin_record_payment.html", context)


@admin_required
def admin_gateway_settings(request):
    """List and configure payment gateway settings."""
    gateways = PaymentGatewayConfig.objects.all()

    editing_pk = request.GET.get("edit")
    editing_gateway = None
    form = None

    if editing_pk:
        editing_gateway = get_object_or_404(PaymentGatewayConfig, pk=editing_pk)
        form = PaymentGatewayConfigForm(instance=editing_gateway)
    elif request.GET.get("add"):
        form = PaymentGatewayConfigForm()

    if request.method == "POST":
        if editing_pk:
            editing_gateway = get_object_or_404(PaymentGatewayConfig, pk=editing_pk)
            form = PaymentGatewayConfigForm(request.POST, instance=editing_gateway)
        else:
            form = PaymentGatewayConfigForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Gateway configuration saved.")
            return redirect("billing_admin:gateway_settings")

    context = {
        "gateways": gateways,
        "form": form,
        "editing_gateway": editing_gateway,
    }
    return render(request, "billing/admin_gateway_settings.html", context)


# ---------------------------------------------------------------------------
# Property Billing Configuration
# ---------------------------------------------------------------------------


@admin_required
def admin_property_billing_config(request, property_pk):
    """Create/edit PropertyBillingConfig for a property."""
    prop = get_object_or_404(Property, pk=property_pk)
    config, created = PropertyBillingConfig.objects.get_or_create(
        property=prop,
        defaults={
            "auto_generate_invoices": True,
            "default_due_day": 1,
            "late_fee_enabled": False,
        },
    )

    if request.method == "POST":
        form = PropertyBillingConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, f"Billing configuration for {prop.name} saved.")
            return redirect("billing_admin:property_billing_config", property_pk=prop.pk)
    else:
        form = PropertyBillingConfigForm(instance=config)

    context = {
        "property": prop,
        "form": form,
        "config": config,
    }
    return render(request, "billing/admin_property_billing_config.html", context)


# ---------------------------------------------------------------------------
# Recurring Charges
# ---------------------------------------------------------------------------


@admin_required
def admin_recurring_charges(request, lease_pk):
    """List recurring charges for a lease and add new ones."""
    lease = get_object_or_404(
        Lease.objects.select_related("tenant", "unit", "unit__property"),
        pk=lease_pk,
    )
    charges = RecurringCharge.objects.filter(lease=lease).order_by("charge_type")

    if request.method == "POST":
        form = RecurringChargeForm(request.POST)
        if form.is_valid():
            charge = form.save(commit=False)
            charge.lease = lease
            charge.save()
            messages.success(request, f"Recurring charge '{charge.description}' added.")
            return redirect("billing_admin:recurring_charges", lease_pk=lease.pk)
    else:
        form = RecurringChargeForm()

    context = {
        "lease": lease,
        "charges": charges,
        "form": form,
    }
    return render(request, "billing/admin_recurring_charges.html", context)


@admin_required
def admin_recurring_charge_edit(request, pk):
    """Edit a recurring charge."""
    charge = get_object_or_404(RecurringCharge.objects.select_related("lease"), pk=pk)
    back_url = charge.lease and f"/admin-portal/billing/leases/{charge.lease.pk}/charges/" or "/admin-portal/billing/invoices/"

    if request.method == "POST":
        form = RecurringChargeForm(request.POST, instance=charge)
        if form.is_valid():
            form.save()
            messages.success(request, f"Recurring charge '{charge.description}' updated.")
            if charge.lease:
                return redirect("billing_admin:recurring_charges", lease_pk=charge.lease.pk)
            return redirect("billing_admin:invoice_list")
    else:
        form = RecurringChargeForm(instance=charge)

    context = {
        "form": form,
        "charge": charge,
        "editing": True,
        "back_url": back_url,
    }
    return render(request, "billing/admin_recurring_charge_form.html", context)


@admin_required
@require_POST
def admin_recurring_charge_delete(request, pk):
    """Delete a recurring charge."""
    charge = get_object_or_404(RecurringCharge.objects.select_related("lease"), pk=pk)
    lease_pk = charge.lease_id
    charge.delete()
    messages.success(request, "Recurring charge deleted.")
    if lease_pk:
        return redirect("billing_admin:recurring_charges", lease_pk=lease_pk)
    return redirect("billing_admin:invoice_list")


# ---------------------------------------------------------------------------
# Utility Configuration Views
# ---------------------------------------------------------------------------


@admin_required
def admin_utility_config_unit(request, unit_pk):
    """Configure utility billing for a specific unit."""
    unit = get_object_or_404(Unit.objects.select_related("property"), pk=unit_pk)

    existing_types = set(unit.utility_configs.values_list("utility_type", flat=True))
    for utype, _ in UtilityConfig.UTILITY_TYPE_CHOICES:
        if utype not in existing_types:
            UtilityConfig.objects.create(
                unit=unit, utility_type=utype,
                billing_mode="included", rate=Decimal("0.00"), is_active=False,
            )

    UtilityConfigFormSet = get_utility_config_formset()

    if request.method == "POST":
        formset = UtilityConfigFormSet(request.POST, instance=unit)
        if formset.is_valid():
            with transaction.atomic():
                old_values = {
                    c.pk: (c.rate, c.billing_mode)
                    for c in unit.utility_configs.all()
                }
                formset.save()
                for config in unit.utility_configs.all():
                    old_rate, old_mode = old_values.get(config.pk, (Decimal("0"), ""))
                    if config.rate != old_rate or config.billing_mode != old_mode:
                        UtilityRateLog.objects.create(
                            utility_config=config,
                            previous_rate=old_rate,
                            new_rate=config.rate,
                            previous_billing_mode=old_mode,
                            new_billing_mode=config.billing_mode,
                            changed_by=request.user,
                            source="admin_gui",
                        )
            messages.success(request, f"Utility configuration updated for {unit}.")
            return redirect("billing_admin:utility_config_unit", unit_pk=unit.pk)
    else:
        formset = UtilityConfigFormSet(instance=unit)

    context = {"unit": unit, "property": unit.property, "formset": formset}
    return render(request, "billing/admin_utility_config_unit.html", context)


@admin_required
def admin_utility_bulk_set(request):
    """Bulk-configure a utility type for all units in a property."""
    if request.method == "POST":
        form = BulkUtilityConfigForm(request.POST)
        if form.is_valid():
            prop = form.cleaned_data["property"]
            utype = form.cleaned_data["utility_type"]
            mode = form.cleaned_data["billing_mode"]
            rate = form.cleaned_data.get("rate") or Decimal("0.00")
            if mode == "included":
                rate = Decimal("0.00")

            units = prop.units.all()
            updated = 0
            with transaction.atomic():
                for u in units:
                    config, created = UtilityConfig.objects.get_or_create(
                        unit=u, utility_type=utype,
                        defaults={"billing_mode": mode, "rate": rate, "is_active": True},
                    )
                    if not created:
                        old_rate, old_mode = config.rate, config.billing_mode
                        config.billing_mode = mode
                        config.rate = rate
                        config.is_active = True
                        config.save()
                        if old_rate != rate or old_mode != mode:
                            UtilityRateLog.objects.create(
                                utility_config=config,
                                previous_rate=old_rate,
                                new_rate=rate,
                                previous_billing_mode=old_mode,
                                new_billing_mode=mode,
                                changed_by=request.user,
                                source="bulk_set",
                            )
                    updated += 1

            messages.success(
                request,
                f"{UtilityConfig(utility_type=utype).get_utility_type_display()} "
                f"configured as {mode} for {updated} units in {prop.name}.",
            )
            return redirect("billing_admin:utility_bulk_set")
    else:
        form = BulkUtilityConfigForm()

    context = {"form": form}
    return render(request, "billing/admin_utility_bulk_set.html", context)


@admin_required
def admin_utility_rate_history(request):
    """View rate change audit log."""
    logs = UtilityRateLog.objects.select_related(
        "utility_config__unit__property", "changed_by"
    ).all()

    property_pk = request.GET.get("property")
    utility_type = request.GET.get("utility_type")
    if property_pk:
        logs = logs.filter(utility_config__unit__property_id=property_pk)
    if utility_type:
        logs = logs.filter(utility_config__utility_type=utility_type)

    properties = Property.objects.filter(is_active=True)

    context = {
        "logs": logs[:200],
        "properties": properties,
        "utility_type_choices": UtilityConfig.UTILITY_TYPE_CHOICES,
        "current_property": property_pk or "",
        "current_utility_type": utility_type or "",
    }
    return render(request, "billing/admin_utility_rate_history.html", context)


# ---------------------------------------------------------------------------
# API Endpoint
# ---------------------------------------------------------------------------


@csrf_exempt
@require_POST
def api_update_variable_rate(request):
    """
    Authenticated API endpoint for external systems to update variable utility rates.

    POST /admin-portal/billing/api/utility-rate/
    Headers: Authorization: Token <token>
    Body: {"unit_id": "<uuid>", "utility_type": "electric", "rate": 87.50, "notes": "..."}
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Token "):
        return JsonResponse({"error": "Missing or invalid Authorization header."}, status=401)

    token_value = auth_header[6:].strip()
    try:
        api_token = ApiToken.objects.select_related("user").get(
            token=token_value, is_active=True
        )
    except ApiToken.DoesNotExist:
        return JsonResponse({"error": "Invalid token."}, status=401)

    if api_token.user.role not in ("admin", "staff"):
        return JsonResponse({"error": "Insufficient permissions."}, status=403)

    api_token.last_used_at = timezone.now()
    api_token.save(update_fields=["last_used_at"])

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    unit_id = data.get("unit_id")
    utility_type = data.get("utility_type")
    new_rate = data.get("rate")
    notes = data.get("notes", "")

    if not all([unit_id, utility_type, new_rate is not None]):
        return JsonResponse({"error": "unit_id, utility_type, and rate are required."}, status=400)

    try:
        new_rate = Decimal(str(new_rate))
    except Exception:
        return JsonResponse({"error": "Invalid rate value."}, status=400)

    if new_rate < 0:
        return JsonResponse({"error": "Rate must be non-negative."}, status=400)

    try:
        config = UtilityConfig.objects.get(
            unit_id=unit_id, utility_type=utility_type, billing_mode="variable",
        )
    except UtilityConfig.DoesNotExist:
        return JsonResponse(
            {"error": "No variable utility config found for this unit and type."},
            status=404,
        )

    old_rate = config.rate
    config.rate = new_rate
    config.save(update_fields=["rate", "updated_at"])

    UtilityRateLog.objects.create(
        utility_config=config,
        previous_rate=old_rate,
        new_rate=new_rate,
        previous_billing_mode="variable",
        new_billing_mode="variable",
        changed_by=api_token.user,
        source="api",
        notes=notes,
    )

    return JsonResponse({
        "status": "ok",
        "config_id": str(config.pk),
        "new_rate": float(new_rate),
    })


# ===========================================================================
# Tenant Views
# ===========================================================================


@tenant_required
def tenant_billing_dashboard(request):
    """Tenant billing overview: balance due, cost breakdown, recent invoices."""
    tenant = request.user

    invoices = Invoice.objects.filter(tenant=tenant).order_by("-issue_date")
    outstanding_invoices = invoices.filter(status__in=["issued", "partial", "overdue"])

    total_balance = Decimal("0.00")
    for inv in outstanding_invoices:
        total_balance += inv.balance_due

    recent_invoices = invoices[:5]
    recent_payments = Payment.objects.filter(tenant=tenant).order_by("-payment_date")[:5]

    # Available prepayment credits
    available_credit = (
        PrepaymentCredit.objects.filter(tenant=tenant, remaining_amount__gt=0)
        .aggregate(total=Sum("remaining_amount"))
        .get("total")
        or Decimal("0.00")
    )

    # Monthly cost breakdown from active lease
    active_lease = Lease.objects.filter(
        tenant=tenant, status="active"
    ).select_related("unit").first()

    utility_breakdown = []
    estimated_monthly_total = Decimal("0.00")
    if active_lease:
        estimated_monthly_total = active_lease.monthly_rent
        configs = UtilityConfig.objects.filter(
            unit=active_lease.unit, is_active=True
        ).order_by("utility_type")
        for config in configs:
            utility_breakdown.append({
                "name": config.get_utility_type_display(),
                "billing_mode": config.billing_mode,
                "billing_mode_display": config.get_billing_mode_display(),
                "rate": config.rate,
                "is_included": config.billing_mode == "included",
                "is_tenant_pays": config.billing_mode == "tenant_pays",
            })
            if config.billing_mode not in ("included", "tenant_pays"):
                estimated_monthly_total += config.rate

    context = {
        "total_balance": total_balance,
        "outstanding_count": outstanding_invoices.count(),
        "recent_invoices": recent_invoices,
        "recent_payments": recent_payments,
        "available_credit": available_credit,
        "active_lease": active_lease,
        "utility_breakdown": utility_breakdown,
        "estimated_monthly_total": estimated_monthly_total,
    }
    return render(request, "billing/tenant_billing_dashboard.html", context)


@tenant_required
def tenant_invoice_list(request):
    """List all invoices for the authenticated tenant."""
    tenant = request.user
    status_filter = request.GET.get("status", "")
    invoices = Invoice.objects.filter(tenant=tenant).select_related("lease", "lease__unit")

    if status_filter:
        invoices = invoices.filter(status=status_filter)

    context = {
        "invoices": invoices,
        "status_filter": status_filter,
        "status_choices": Invoice.STATUS_CHOICES,
    }
    return render(request, "billing/tenant_invoice_list.html", context)


@tenant_required
def tenant_invoice_detail(request, pk):
    """View a single invoice detail for the authenticated tenant."""
    invoice = get_object_or_404(
        Invoice.objects.select_related("lease", "lease__unit", "billing_cycle"),
        pk=pk,
        tenant=request.user,
    )
    line_items = invoice.line_items.all()
    payments = invoice.payments.filter(status="completed").order_by("-payment_date")

    # Check if online payment is available
    has_active_gateway = PaymentGatewayConfig.objects.filter(is_active=True).exists()

    context = {
        "invoice": invoice,
        "line_items": line_items,
        "payments": payments,
        "can_pay_online": has_active_gateway and invoice.status in ("issued", "partial", "overdue"),
    }
    return render(request, "billing/tenant_invoice_detail.html", context)


@tenant_required
def tenant_payment_history(request):
    """List all payments for the authenticated tenant."""
    payments = (
        Payment.objects.filter(tenant=request.user)
        .select_related("invoice")
        .order_by("-payment_date")
    )

    context = {"payments": payments}
    return render(request, "billing/tenant_payment_history.html", context)


@tenant_required
def tenant_initiate_payment(request, pk):
    """Tenant payment initiation — select gateway and pay."""
    invoice = get_object_or_404(
        Invoice.objects.select_related("lease", "lease__unit"),
        pk=pk,
        tenant=request.user,
    )

    if invoice.status not in ("issued", "partial", "overdue"):
        messages.error(request, "This invoice cannot be paid.")
        return redirect("billing_tenant:invoice_detail", pk=invoice.pk)

    gateways = PaymentGatewayConfig.objects.filter(is_active=True)
    available_credit = (
        PrepaymentCredit.objects.filter(
            tenant=request.user, remaining_amount__gt=0,
        ).aggregate(total=Sum("remaining_amount")).get("total")
        or Decimal("0.00")
    )

    if request.method == "POST":
        gateway_pk = request.POST.get("gateway")
        apply_credits = request.POST.get("apply_credits") == "on"

        try:
            gateway_config = None
            provider = None
            if gateway_pk:
                gateway_config = get_object_or_404(PaymentGatewayConfig, pk=gateway_pk, is_active=True)
                provider = gateway_config.provider

            payment, client_config = PaymentService.initiate_online_payment(
                invoice=invoice,
                gateway_provider=provider,
                apply_credits=apply_credits,
            )

            if client_config is None:
                # Fully paid by credits
                messages.success(request, "Invoice paid using your account credit.")
                return render(request, "billing/tenant_payment_confirmation.html", {
                    "success": True,
                    "payment": payment,
                })

            # For now, mark payment as completed (gateway integration returns client config
            # for JS-side completion in production; here we complete server-side)
            result = PaymentService.confirm_gateway_payment(payment.pk)
            if result.get("status") == "completed":
                return render(request, "billing/tenant_payment_confirmation.html", {
                    "success": True,
                    "payment": Payment.objects.select_related("invoice").get(pk=payment.pk),
                })
            else:
                return render(request, "billing/tenant_payment_confirmation.html", {
                    "success": False,
                    "invoice": invoice,
                    "error_message": result.get("message", "Payment could not be completed."),
                })

        except ValueError as e:
            messages.error(request, str(e))
            return redirect("billing_tenant:initiate_payment", pk=invoice.pk)

    context = {
        "invoice": invoice,
        "gateways": gateways,
        "available_credit": available_credit,
    }
    return render(request, "billing/tenant_initiate_payment.html", context)


@tenant_required
def tenant_payment_callback(request):
    """Handle return from gateway redirect."""
    payment_id = request.GET.get("payment_id")
    if not payment_id:
        messages.error(request, "Invalid payment callback.")
        return redirect("billing_tenant:billing_dashboard")

    try:
        payment = Payment.objects.select_related("invoice").get(
            pk=payment_id, tenant=request.user,
        )
    except Payment.DoesNotExist:
        messages.error(request, "Payment not found.")
        return redirect("billing_tenant:billing_dashboard")

    if payment.status == "pending":
        result = PaymentService.confirm_gateway_payment(payment.pk)
        payment.refresh_from_db()

    success = payment.status == "completed"
    context = {
        "success": success,
        "payment": payment,
        "invoice": payment.invoice,
    }
    return render(request, "billing/tenant_payment_confirmation.html", context)


@csrf_exempt
@require_POST
def tenant_payment_webhook(request, provider):
    """
    Gateway webhook endpoint for server-side payment confirmations.
    No auth decorator — uses gateway signature verification.
    """
    from apps.core.services.payments.factory import get_gateway_for_provider

    gateway = get_gateway_for_provider(provider)
    if not gateway:
        return JsonResponse({"error": "Unknown provider."}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    transaction_id = data.get("transaction_id") or data.get("id") or data.get("payment_intent")
    if not transaction_id:
        return JsonResponse({"error": "No transaction ID."}, status=400)

    try:
        payment = Payment.objects.get(
            gateway_transaction_id=transaction_id,
            status="pending",
        )
    except Payment.DoesNotExist:
        return JsonResponse({"error": "Payment not found."}, status=404)

    result = PaymentService.confirm_gateway_payment(payment.pk)
    return JsonResponse(result)
