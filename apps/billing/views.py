from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.decorators import admin_required, tenant_required
from apps.leases.models import Lease

from .forms import (
    BatchInvoiceGenerateForm,
    InvoiceForm,
    InvoiceLineItemFormSet,
    PaymentGatewayConfigForm,
    RecordPaymentForm,
)
from .models import (
    BillingCycle,
    Invoice,
    InvoiceLineItem,
    Payment,
    PaymentGatewayConfig,
    PrepaymentCredit,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _generate_invoice_number():
    """Generate a unique invoice number in the format INV-YYYYMM-XXXX."""
    now = timezone.now()
    prefix = f"INV-{now.strftime('%Y%m')}-"
    last_invoice = (
        Invoice.objects.filter(invoice_number__startswith=prefix)
        .order_by("-invoice_number")
        .first()
    )
    if last_invoice:
        last_seq = int(last_invoice.invoice_number.split("-")[-1])
        seq = last_seq + 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


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

    context = {
        "invoice": invoice,
        "line_items": line_items,
        "payments": payments,
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
                invoice.invoice_number = _generate_invoice_number()
                invoice.tenant = invoice.lease.tenant
                invoice.created_by = request.user
                invoice.save()

                formset = InvoiceLineItemFormSet(request.POST, instance=invoice)
                if formset.is_valid():
                    formset.save()
                    # Recalculate total
                    total = invoice.line_items.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
                    invoice.total_amount = total
                    invoice.save(update_fields=["total_amount"])

                    messages.success(
                        request,
                        f"Invoice {invoice.invoice_number} created successfully.",
                    )
                    return redirect("billing_admin:invoice_detail", pk=invoice.pk)
                else:
                    # Formset invalid -- delete the invoice we just created
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
                    # Skip if invoice already exists for this lease and cycle
                    exists = Invoice.objects.filter(
                        lease=lease, billing_cycle=billing_cycle
                    ).exists()
                    if exists:
                        skipped_count += 1
                        continue

                    invoice = Invoice.objects.create(
                        invoice_number=_generate_invoice_number(),
                        lease=lease,
                        tenant=lease.tenant,
                        billing_cycle=billing_cycle,
                        status="issued",
                        issue_date=timezone.now().date(),
                        due_date=billing_cycle.end_date,
                        notes=f"Auto-generated for {billing_cycle.name}",
                        created_by=request.user,
                    )

                    # Create rent line item
                    InvoiceLineItem.objects.create(
                        invoice=invoice,
                        charge_type="rent",
                        description=f"Monthly Rent - {lease.unit}",
                        quantity=1,
                        unit_price=lease.monthly_rent,
                        amount=lease.monthly_rent,
                    )

                    invoice.total_amount = lease.monthly_rent
                    invoice.save(update_fields=["total_amount"])
                    created_count += 1

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
def admin_payment_list(request):
    """List all payments."""
    payments = Payment.objects.select_related("tenant", "invoice", "gateway_config").all()

    context = {"payments": payments}
    return render(request, "billing/admin_payment_list.html", context)


@admin_required
def admin_record_payment(request):
    """Record a manual payment against an invoice."""
    if request.method == "POST":
        form = RecordPaymentForm(request.POST)
        if form.is_valid():
            invoice = form.cleaned_data["invoice"]
            amount = form.cleaned_data["amount"]
            method = form.cleaned_data["method"]
            reference_number = form.cleaned_data.get("reference_number", "")
            notes = form.cleaned_data.get("notes", "")

            if amount > invoice.balance_due:
                form.add_error(
                    "amount",
                    f"Amount exceeds balance due of ${invoice.balance_due:.2f}.",
                )
            else:
                with transaction.atomic():
                    payment = Payment.objects.create(
                        tenant=invoice.tenant,
                        invoice=invoice,
                        amount=amount,
                        method=method,
                        status="completed",
                        reference_number=reference_number,
                        notes=notes,
                    )

                    invoice.amount_paid += amount
                    if invoice.amount_paid >= invoice.total_amount:
                        invoice.status = "paid"
                    else:
                        invoice.status = "partial"
                    invoice.save(update_fields=["amount_paid", "status"])

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

    # Handle inline edit / create
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


# ===========================================================================
# Tenant Views
# ===========================================================================


@tenant_required
def tenant_billing_dashboard(request):
    """Tenant billing overview: balance due, recent invoices, quick pay."""
    tenant = request.user

    invoices = Invoice.objects.filter(tenant=tenant).order_by("-issue_date")
    outstanding_invoices = invoices.filter(status__in=["issued", "partial", "overdue"])

    total_balance = Decimal("0.00")
    for inv in outstanding_invoices:
        total_balance += inv.balance_due

    recent_invoices = invoices[:5]
    recent_payments = Payment.objects.filter(tenant=tenant).order_by("-payment_date")[:5]

    context = {
        "total_balance": total_balance,
        "outstanding_count": outstanding_invoices.count(),
        "recent_invoices": recent_invoices,
        "recent_payments": recent_payments,
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

    context = {
        "invoice": invoice,
        "line_items": line_items,
        "payments": payments,
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
