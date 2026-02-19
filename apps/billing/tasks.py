"""
Django-Q2 async tasks for the billing app.

Schedule these via Django-Q2 admin or programmatically:
    from django_q.tasks import async_task, schedule
    async_task('apps.billing.tasks.generate_monthly_invoices', billing_cycle_id)
    async_task('apps.billing.tasks.check_overdue_invoices')
    async_task('apps.billing.tasks.process_payment', payment_id)
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def _generate_invoice_number():
    """Generate a unique invoice number in the format INV-YYYYMM-XXXX."""
    from .models import Invoice

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


def generate_monthly_invoices(billing_cycle_id):
    """
    Create invoices for all active leases within the given billing cycle.

    Args:
        billing_cycle_id: UUID of the BillingCycle to generate invoices for.

    Returns:
        dict with created and skipped counts.
    """
    from apps.leases.models import Lease

    from .models import BillingCycle, Invoice, InvoiceLineItem

    try:
        billing_cycle = BillingCycle.objects.get(pk=billing_cycle_id)
    except BillingCycle.DoesNotExist:
        logger.error("BillingCycle %s not found.", billing_cycle_id)
        return {"error": f"BillingCycle {billing_cycle_id} not found."}

    if billing_cycle.is_closed:
        logger.warning("BillingCycle %s is already closed.", billing_cycle_id)
        return {"error": "Billing cycle is closed."}

    active_leases = Lease.objects.filter(status="active").select_related("tenant", "unit")
    created_count = 0
    skipped_count = 0

    with transaction.atomic():
        for lease in active_leases:
            # Skip if an invoice already exists for this lease + cycle
            if Invoice.objects.filter(lease=lease, billing_cycle=billing_cycle).exists():
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
            )

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

    logger.info(
        "generate_monthly_invoices complete for cycle %s: %d created, %d skipped.",
        billing_cycle.name,
        created_count,
        skipped_count,
    )
    return {"created": created_count, "skipped": skipped_count}


def check_overdue_invoices():
    """
    Mark invoices as overdue if past the due date and not yet fully paid.

    Returns:
        dict with the count of newly overdue invoices.
    """
    from .models import Invoice

    today = timezone.now().date()
    overdue_qs = Invoice.objects.filter(
        status__in=["issued", "partial"],
        due_date__lt=today,
    )

    count = overdue_qs.update(status="overdue")

    logger.info("check_overdue_invoices: %d invoices marked as overdue.", count)
    return {"overdue_count": count}


def process_payment(payment_id):
    """
    Process a payment through the configured gateway.

    For online payments with a gateway configuration, this task would
    call the gateway API. For manual payments (cash, check, etc.) it
    simply marks the payment as completed and updates the invoice.

    Args:
        payment_id: UUID of the Payment to process.

    Returns:
        dict with processing result.
    """
    from .models import Payment

    try:
        payment = Payment.objects.select_related("invoice", "gateway_config").get(pk=payment_id)
    except Payment.DoesNotExist:
        logger.error("Payment %s not found.", payment_id)
        return {"error": f"Payment {payment_id} not found."}

    if payment.status != "pending":
        logger.warning("Payment %s is not pending (status=%s).", payment_id, payment.status)
        return {"error": f"Payment is already {payment.status}."}

    invoice = payment.invoice

    try:
        with transaction.atomic():
            if payment.gateway_config and payment.method == "online":
                # In a real implementation, this would call the gateway API:
                #   gateway = get_gateway_client(payment.gateway_config)
                #   result = gateway.charge(amount=payment.amount, ...)
                #   payment.gateway_transaction_id = result.transaction_id
                logger.info(
                    "Processing online payment %s via %s (stub).",
                    payment_id,
                    payment.gateway_config.provider,
                )
                payment.gateway_transaction_id = f"sim_{payment_id}"

            payment.status = "completed"
            payment.save(update_fields=["status", "gateway_transaction_id"])

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
