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
    GatewayBaseForm,
    InvoiceEditLineItemFormSet,
    InvoiceForm,
    InvoiceLineItemFormSet,
    PROVIDER_FORM_MAP,
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
    BitcoinPayment,
    BitcoinPriceSnapshot,
    BitcoinWalletConfig,
    Invoice,
    InvoiceLineItem,
    Payment,
    PaymentGatewayConfig,
    PrepaymentCredit,
    PropertyBillingConfig,
    RecurringCharge,
    UtilityConfig,
    UtilityRateLog,
    WebhookEvent,
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
            failed_leases = []

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
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.exception(
                            "Failed to create invoice for lease %s: %s",
                            lease.pk, str(e)
                        )
                        skipped_count += 1
                        failed_leases.append(f"{lease.tenant.get_full_name() if lease.tenant else 'Unknown'}: {str(e)}")

            if failed_leases:
                messages.warning(
                    request,
                    f"Batch generation complete: {created_count} invoices created, "
                    f"{skipped_count} skipped. {len(failed_leases)} failed: {', '.join(failed_leases[:3])}"
                    + (" and more..." if len(failed_leases) > 3 else ""),
                )
            else:
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
    provider = request.GET.get("provider")
    show_add = request.GET.get("add")

    base_form = None
    config_form = None
    editing_gateway = None

    if editing_pk:
        editing_gateway = get_object_or_404(PaymentGatewayConfig, pk=editing_pk)
        provider = editing_gateway.provider
        base_form = GatewayBaseForm(instance=editing_gateway)
        FormClass = PROVIDER_FORM_MAP.get(provider)
        if FormClass:
            config_form = FormClass(config_data=editing_gateway.config)
    elif provider and provider in PROVIDER_FORM_MAP:
        base_form = GatewayBaseForm()
        FormClass = PROVIDER_FORM_MAP[provider]
        config_form = FormClass()

    if request.method == "POST" and (editing_pk or provider):
        if editing_pk:
            editing_gateway = get_object_or_404(PaymentGatewayConfig, pk=editing_pk)
            provider = editing_gateway.provider
            base_form = GatewayBaseForm(request.POST, instance=editing_gateway)
        else:
            base_form = GatewayBaseForm(request.POST)

        FormClass = PROVIDER_FORM_MAP.get(provider)
        config_form = FormClass(request.POST) if FormClass else None

        if base_form.is_valid() and (config_form is None or config_form.is_valid()):
            gateway = base_form.save(commit=False)
            if not editing_pk:
                gateway.provider = provider
            if config_form:
                gateway.config = config_form.get_config_data()
            gateway.save()
            messages.success(request, "Gateway configuration saved.")
            return redirect("billing_admin:gateway_settings")

    # Provider display info for the selection cards
    provider_info = {
        "stripe": {"icon": "bi-stripe", "color": "primary", "desc": "Credit/debit cards, Apple Pay, Google Pay"},
        "paypal": {"icon": "bi-paypal", "color": "info", "desc": "PayPal checkout and payments"},
        "square": {"icon": "bi-grid-3x3", "color": "dark", "desc": "In-person and online payments"},
        "authorize_net": {"icon": "bi-credit-card-2-front", "color": "danger", "desc": "Credit/debit card processing"},
        "braintree": {"icon": "bi-tree", "color": "success", "desc": "PayPal-owned payment platform"},
        "plaid_ach": {"icon": "bi-bank", "color": "secondary", "desc": "ACH direct bank transfers via Plaid"},
        "bitcoin": {"icon": "bi-currency-bitcoin", "color": "warning", "desc": "Bitcoin cryptocurrency payments"},
    }

    context = {
        "gateways": gateways,
        "base_form": base_form,
        "config_form": config_form,
        "editing_gateway": editing_gateway,
        "show_add": show_add,
        "provider": provider,
        "provider_info": provider_info,
        "provider_choices": PaymentGatewayConfig.PROVIDER_CHOICES,
    }
    return render(request, "billing/admin_gateway_settings.html", context)


@admin_required
@require_POST
def admin_gateway_test(request, pk):
    """Test gateway connection."""
    from apps.core.services.payments.factory import get_gateway_class
    config = get_object_or_404(PaymentGatewayConfig, pk=pk)
    try:
        cls = get_gateway_class(config.provider)
        gateway = cls(config)
        success, message = gateway.test_connection()
        return JsonResponse({"success": success, "message": message})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})


@admin_required
def admin_webhook_log(request):
    """List webhook events with filters."""
    events = WebhookEvent.objects.select_related("payment").all()

    provider = request.GET.get("provider")
    status = request.GET.get("status")

    if provider:
        events = events.filter(provider=provider)
    if status:
        events = events.filter(status=status)

    context = {
        "events": events[:200],
        "provider_filter": provider,
        "status_filter": status,
        "provider_choices": PaymentGatewayConfig.PROVIDER_CHOICES,
        "status_choices": WebhookEvent.WEBHOOK_STATUS_CHOICES,
    }
    return render(request, "billing/admin_webhook_log.html", context)


@admin_required
def admin_bitcoin_dashboard(request):
    """Bitcoin wallet overview."""
    from apps.core.services.payments.bitcoin_utils import get_btc_usd_rate

    btc_config = PaymentGatewayConfig.objects.filter(provider="bitcoin", is_active=True).first()
    wallet_config = None
    if btc_config:
        wallet_config = getattr(btc_config, 'btc_wallet_config', None)

    recent_payments = BitcoinPayment.objects.select_related("invoice", "invoice__tenant")[:20]
    pending_count = BitcoinPayment.objects.filter(status__in=["pending", "mempool"]).count()

    try:
        btc_usd_rate = get_btc_usd_rate()
    except Exception:
        btc_usd_rate = None

    context = {
        "btc_config": btc_config,
        "wallet_config": wallet_config,
        "recent_payments": recent_payments,
        "pending_count": pending_count,
        "btc_usd_rate": btc_usd_rate,
    }
    return render(request, "billing/admin_bitcoin_dashboard.html", context)


@admin_required
def admin_bitcoin_transfer(request):
    """Transfer BTC out of the wallet."""
    from apps.core.services.payments.bitcoin_utils import get_btc_usd_rate

    btc_config = PaymentGatewayConfig.objects.filter(provider="bitcoin", is_active=True).first()

    try:
        btc_usd_rate = get_btc_usd_rate()
    except Exception:
        btc_usd_rate = None

    if request.method == "POST":
        destination = request.POST.get("destination_address", "").strip()
        amount_btc = request.POST.get("amount_btc", "").strip()

        if not destination or not amount_btc:
            messages.error(request, "Destination address and amount are required.")
        else:
            # For now, manual transfer - just log it
            messages.info(request, f"Transfer request recorded: {amount_btc} BTC to {destination}. This requires manual processing with your offline signing key.")

        return redirect("billing_admin:bitcoin_transfer")

    context = {
        "btc_config": btc_config,
        "btc_usd_rate": btc_usd_rate,
    }
    return render(request, "billing/admin_bitcoin_transfer.html", context)


@admin_required
def admin_bitcoin_payments(request):
    """List all Bitcoin payments."""
    payments = BitcoinPayment.objects.select_related(
        "invoice", "invoice__tenant", "payment"
    ).all()

    status = request.GET.get("status")
    if status:
        payments = payments.filter(status=status)

    context = {
        "btc_payments": payments[:200],
        "status_filter": status,
        "status_choices": BitcoinPayment.STATUS_CHOICES,
    }
    return render(request, "billing/admin_bitcoin_payments.html", context)


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

    # Reward balance
    from apps.rewards.services import RewardService

    reward_balance_obj = RewardService.get_or_create_balance(tenant)
    reward_balance = reward_balance_obj.balance

    context = {
        "total_balance": total_balance,
        "outstanding_count": outstanding_invoices.count(),
        "recent_invoices": recent_invoices,
        "recent_payments": recent_payments,
        "available_credit": available_credit,
        "reward_balance": reward_balance,
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

    # Get available reward balance
    from apps.rewards.services import RewardService

    reward_balance_obj = RewardService.get_or_create_balance(request.user)
    available_rewards = reward_balance_obj.balance

    if request.method == "POST":
        gateway_pk = request.POST.get("gateway")
        apply_credits = request.POST.get("apply_credits") == "on"
        apply_rewards = request.POST.get("apply_rewards") == "on"

        try:
            # Apply rewards first (before credits and gateway)
            if apply_rewards and available_rewards > 0:
                RewardService.apply_rewards_to_invoice(
                    invoice=invoice,
                    applied_by=request.user,
                )
                invoice.refresh_from_db()
                if invoice.balance_due <= 0:
                    messages.success(request, "Invoice paid using your reward balance.")
                    return render(request, "billing/tenant_payment_confirmation.html", {
                        "success": True,
                        "payment": invoice.payments.order_by("-payment_date").first(),
                    })

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
        "available_rewards": available_rewards,
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

    ip_address = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", ""))
    if "," in ip_address:
        ip_address = ip_address.split(",")[0].strip()

    # Verify webhook signature
    try:
        event_data = gateway.verify_webhook(request)
    except ValueError as e:
        WebhookEvent.objects.create(
            provider=provider,
            event_type="verification_failed",
            payload={"error": str(e)},
            status="failed",
            error_message=str(e),
            ip_address=ip_address,
        )
        return JsonResponse({"error": "Signature verification failed."}, status=403)

    event_type = event_data.get("event_type", "")
    transaction_id = event_data.get("transaction_id", "")
    event_id = event_data.get("raw_event", {}).get("id", "")

    # Deduplicate
    if event_id:
        existing = WebhookEvent.objects.filter(event_id=event_id, status="processed").first()
        if existing:
            return JsonResponse({"status": "already_processed"})

    # Log the event
    webhook_event = WebhookEvent.objects.create(
        provider=provider,
        event_type=event_type,
        event_id=event_id,
        payload=event_data.get("raw_event", {}),
        status="received",
        ip_address=ip_address,
    )

    if not transaction_id:
        webhook_event.status = "ignored"
        webhook_event.error_message = "No transaction ID in event"
        webhook_event.save(update_fields=["status", "error_message"])
        return JsonResponse({"status": "ignored"})

    try:
        payment = Payment.objects.get(
            gateway_transaction_id=transaction_id,
            status="pending",
        )
        result = PaymentService.confirm_gateway_payment(payment.pk)
        webhook_event.payment = payment
        webhook_event.status = "processed"
        webhook_event.save(update_fields=["payment", "status"])
        return JsonResponse(result)
    except Payment.DoesNotExist:
        webhook_event.status = "ignored"
        webhook_event.error_message = f"No pending payment for transaction {transaction_id}"
        webhook_event.save(update_fields=["status", "error_message"])
        return JsonResponse({"status": "no_matching_payment"})
    except Exception as e:
        webhook_event.status = "failed"
        webhook_event.error_message = str(e)
        webhook_event.save(update_fields=["status", "error_message"])
        return JsonResponse({"error": str(e)}, status=500)
