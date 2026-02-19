"""
Django-Q2 async tasks for the billing app.

Schedule these via Django-Q2 admin or programmatically:
    from django_q.tasks import async_task, schedule
    async_task('apps.billing.tasks.generate_monthly_invoices')
    async_task('apps.billing.tasks.apply_late_fees')
    async_task('apps.billing.tasks.process_payment', payment_id)
"""

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def generate_monthly_invoices(target_month=None):
    """
    Auto-generate invoices for all eligible properties/leases.

    Called by Django-Q2 schedule on the 1st of each month.
    Iterates properties with auto_generate_invoices=True, auto-creates
    BillingCycle per property, delegates to InvoiceService.

    Args:
        target_month: Optional date in the target month. Defaults to current month.

    Returns:
        dict with created, skipped, and error counts.
    """
    from apps.leases.models import Lease

    from .models import BillingCycle, Invoice, PropertyBillingConfig
    from .services import InvoiceService

    if target_month is None:
        target_month = timezone.now().date()

    cycle_start = target_month.replace(day=1)
    cycle_end = (cycle_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    configs = PropertyBillingConfig.objects.filter(
        auto_generate_invoices=True,
        property__is_active=True,
    ).select_related("property")

    results = {"created": 0, "skipped": 0, "errors": []}

    for config in configs:
        prop = config.property

        billing_cycle, _ = BillingCycle.objects.get_or_create(
            property=prop,
            start_date=cycle_start,
            end_date=cycle_end,
            defaults={"name": f"{prop.name} - {cycle_start.strftime('%B %Y')}"},
        )

        if billing_cycle.is_closed:
            results["skipped"] += 1
            continue

        active_leases = Lease.objects.filter(
            unit__property=prop, status="active",
        ).select_related("tenant", "unit")

        for lease in active_leases:
            if Invoice.objects.filter(lease=lease, billing_cycle=billing_cycle).exists():
                results["skipped"] += 1
                continue

            try:
                due_day = min(config.default_due_day, 28)
                due_date = target_month.replace(day=due_day)
                notes = config.default_invoice_notes

                InvoiceService.create_invoice_for_lease(
                    lease=lease,
                    billing_cycle=billing_cycle,
                    issue_date=cycle_start,
                    due_date=due_date,
                    notes=notes,
                )
                results["created"] += 1
            except Exception as e:
                logger.exception("Error generating invoice for lease %s", lease.pk)
                results["errors"].append(str(e))

    logger.info(
        "generate_monthly_invoices: %d created, %d skipped, %d errors.",
        results["created"],
        results["skipped"],
        len(results["errors"]),
    )
    return results


def apply_late_fees():
    """
    Daily task: mark overdue invoices and apply late fees/interest per property config.

    Returns:
        dict with overdue_marked and fees_applied counts.
    """
    from .models import Invoice
    from .services import LateFeeService

    today = timezone.now().date()

    # Mark newly overdue invoices
    overdue_count = Invoice.objects.filter(
        status__in=["issued", "partial"],
        due_date__lt=today,
    ).update(status="overdue")

    # Apply late fees + interest to all overdue/partial invoices
    overdue_invoices = Invoice.objects.filter(
        status__in=["overdue", "partial"],
    ).select_related("lease__unit__property")

    fees_applied = 0
    for invoice in overdue_invoices:
        try:
            result = LateFeeService.apply_late_fees_for_invoice(invoice)
            if result:
                fees_applied += 1
        except Exception:
            logger.exception("Failed to apply late fee to invoice %s", invoice.pk)

        try:
            result = LateFeeService.apply_interest_for_invoice(invoice)
            if result:
                fees_applied += 1
        except Exception:
            logger.exception("Failed to apply interest to invoice %s", invoice.pk)

    logger.info(
        "apply_late_fees: %d invoices marked overdue, %d fees/interest applied.",
        overdue_count,
        fees_applied,
    )
    return {"overdue_marked": overdue_count, "fees_applied": fees_applied}


def check_overdue_invoices():
    """
    Mark invoices as overdue if past the due date and not yet fully paid.
    Kept for backward compatibility — logic now lives in apply_late_fees().

    Returns:
        dict with the count of newly overdue invoices.
    """
    from .models import Invoice

    today = timezone.now().date()
    count = Invoice.objects.filter(
        status__in=["issued", "partial"],
        due_date__lt=today,
    ).update(status="overdue")

    logger.info("check_overdue_invoices: %d invoices marked as overdue.", count)
    return {"overdue_count": count}


def process_payment(payment_id):
    """
    Process a payment through the configured gateway or mark manual payment complete.

    Args:
        payment_id: UUID of the Payment to process.

    Returns:
        dict with processing result.
    """
    from .models import Payment
    from .services import PaymentService

    try:
        payment = Payment.objects.select_related(
            "invoice", "gateway_config"
        ).get(pk=payment_id)
    except Payment.DoesNotExist:
        logger.error("Payment %s not found.", payment_id)
        return {"error": f"Payment {payment_id} not found."}

    if payment.status != "pending":
        logger.warning("Payment %s is not pending (status=%s).", payment_id, payment.status)
        return {"error": f"Payment is already {payment.status}."}

    if payment.gateway_config and payment.method == "online":
        return PaymentService.confirm_gateway_payment(payment.pk)

    # Manual payment — mark as completed and update invoice
    try:
        with transaction.atomic():
            payment.status = "completed"
            payment.save(update_fields=["status"])

            invoice = payment.invoice
            invoice.amount_paid += payment.amount
            if invoice.amount_paid >= invoice.total_amount:
                invoice.status = "paid"
            else:
                invoice.status = "partial"
            invoice.save(update_fields=["amount_paid", "status"])

        logger.info("Payment %s processed successfully.", payment_id)
        return {"status": "completed", "payment_id": str(payment_id)}

    except Exception:
        logger.exception("Error processing payment %s.", payment_id)
        payment.status = "failed"
        payment.save(update_fields=["status"])
        return {"status": "failed", "payment_id": str(payment_id)}


def auto_apply_prepayment_credits():
    """
    For newly issued invoices, automatically apply any available prepayment credits.
    Run daily after generate_monthly_invoices.

    Returns:
        dict with credits_applied count.
    """
    from .models import Invoice, Payment, PrepaymentCredit
    from .services import PaymentService

    # Find tenants with both outstanding invoices and available credits
    tenants_with_credits = PrepaymentCredit.objects.filter(
        remaining_amount__gt=0,
    ).values_list("tenant_id", flat=True).distinct()

    invoices = Invoice.objects.filter(
        status="issued",
        tenant_id__in=tenants_with_credits,
    ).select_related("tenant")

    applied_count = 0
    for invoice in invoices:
        credit_amount = PaymentService._apply_prepayment_credits(invoice)
        if credit_amount > 0:
            Payment.objects.create(
                tenant=invoice.tenant,
                invoice=invoice,
                amount=credit_amount,
                method="credit",
                status="completed",
                credit_applied=credit_amount,
                notes="Auto-applied prepayment credit",
            )
            invoice.amount_paid += credit_amount
            if invoice.amount_paid >= invoice.total_amount:
                invoice.status = "paid"
            else:
                invoice.status = "partial"
            invoice.save(update_fields=["amount_paid", "status"])
            applied_count += 1

    logger.info("auto_apply_prepayment_credits: %d credits applied.", applied_count)
    return {"credits_applied": applied_count}
