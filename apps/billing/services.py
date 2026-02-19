import logging
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class InvoiceService:
    """Centralized invoice creation and line-item management."""

    @staticmethod
    def generate_invoice_number():
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

    @staticmethod
    def create_invoice_for_lease(lease, billing_cycle, issue_date, due_date, notes="", created_by=None):
        """
        Create an invoice for a lease with all applicable recurring charges and utilities.

        Returns the created Invoice instance.
        """
        from .models import Invoice, InvoiceLineItem

        with transaction.atomic():
            invoice = Invoice.objects.create(
                invoice_number=InvoiceService.generate_invoice_number(),
                lease=lease,
                tenant=lease.tenant,
                billing_cycle=billing_cycle,
                status="issued",
                issue_date=issue_date,
                due_date=due_date,
                notes=notes,
                created_by=created_by,
            )

            charges = InvoiceService._gather_charges(lease, issue_date)
            total = Decimal("0.00")
            for charge in charges:
                item = InvoiceLineItem.objects.create(
                    invoice=invoice,
                    charge_type=charge["charge_type"],
                    description=charge["description"],
                    quantity=charge.get("quantity", 1),
                    unit_price=charge["amount"],
                    amount=charge["amount"] * charge.get("quantity", 1),
                    billing_mode=charge.get("billing_mode", ""),
                )
                total += item.amount

            invoice.total_amount = total
            invoice.save(update_fields=["total_amount"])

        return invoice

    @staticmethod
    def _gather_charges(lease, billing_date):
        """
        Collect all applicable charges for a lease:
        1. Lease-specific recurring charges
        2. Property-level recurring charges
        3. UtilityConfig entries (fixed/variable mode)
        """
        from .models import RecurringCharge, UtilityConfig

        charges = []
        prop = lease.unit.property

        # Lease-specific recurring charges
        for rc in RecurringCharge.objects.filter(
            lease=lease, is_active=True, start_date__lte=billing_date,
        ):
            if rc.end_date and rc.end_date < billing_date:
                continue
            if rc.frequency == "monthly" or (
                rc.frequency == "quarterly" and billing_date.month % 3 == rc.start_date.month % 3
            ) or (
                rc.frequency == "annual" and billing_date.month == rc.start_date.month
            ) or rc.frequency == "one_time":
                charges.append({
                    "charge_type": rc.charge_type,
                    "description": rc.description,
                    "amount": rc.amount,
                    "quantity": 1,
                })

        # Property-level recurring charges
        for rc in RecurringCharge.objects.filter(
            property=prop, is_active=True, start_date__lte=billing_date,
        ):
            if rc.end_date and rc.end_date < billing_date:
                continue
            if rc.frequency == "monthly" or (
                rc.frequency == "quarterly" and billing_date.month % 3 == rc.start_date.month % 3
            ) or (
                rc.frequency == "annual" and billing_date.month == rc.start_date.month
            ) or rc.frequency == "one_time":
                charges.append({
                    "charge_type": rc.charge_type,
                    "description": rc.description,
                    "amount": rc.amount,
                    "quantity": 1,
                })

        # Utility configs (fixed/variable billing modes)
        utility_configs = UtilityConfig.objects.filter(
            unit=lease.unit, is_active=True,
        )
        for config in utility_configs:
            if config.billing_mode in ("included", "tenant_pays"):
                continue
            charges.append({
                "charge_type": config.utility_type,
                "description": f"{config.get_utility_type_display()} ({config.get_billing_mode_display()})",
                "amount": config.rate,
                "quantity": 1,
                "billing_mode": config.billing_mode,
            })

        return charges

    @staticmethod
    def add_line_item(invoice, charge_type, description, quantity, unit_price):
        """Add a line item to an existing invoice and recalculate total."""
        from .models import InvoiceLineItem

        if invoice.status in ("paid", "cancelled"):
            raise ValueError(f"Cannot add line items to a {invoice.status} invoice.")

        with transaction.atomic():
            item = InvoiceLineItem.objects.create(
                invoice=invoice,
                charge_type=charge_type,
                description=description,
                quantity=quantity,
                unit_price=unit_price,
                amount=quantity * unit_price,
            )
            invoice.recalculate_total()
        return item

    @staticmethod
    def remove_line_item(invoice, line_item_id):
        """Remove a line item from an existing invoice and recalculate total."""
        from .models import InvoiceLineItem

        if invoice.status in ("paid", "cancelled"):
            raise ValueError(f"Cannot remove line items from a {invoice.status} invoice.")

        with transaction.atomic():
            InvoiceLineItem.objects.filter(pk=line_item_id, invoice=invoice).delete()
            invoice.recalculate_total()


class PaymentService:
    """Centralized payment processing logic."""

    @staticmethod
    def initiate_online_payment(invoice, gateway_provider=None, apply_credits=True):
        """
        Create a Payment record and call the gateway for a client-side token.

        Returns (Payment, client_config) tuple.
        If balance is fully covered by credits, returns (Payment, None).
        """
        from apps.core.services.payments.factory import (
            get_active_gateway,
            get_gateway_for_provider,
        )

        from .models import Payment

        gateway = (
            get_gateway_for_provider(gateway_provider)
            if gateway_provider
            else get_active_gateway()
        )
        if not gateway:
            raise ValueError("No active payment gateway configured.")

        with transaction.atomic():
            credit_amount = Decimal("0.00")
            if apply_credits:
                credit_amount = PaymentService._apply_prepayment_credits(invoice)

            remaining = invoice.balance_due - credit_amount
            if remaining <= Decimal("0.00"):
                # Fully covered by credits
                payment = Payment.objects.create(
                    tenant=invoice.tenant,
                    invoice=invoice,
                    amount=credit_amount,
                    method="credit",
                    status="completed",
                    credit_applied=credit_amount,
                    notes="Fully paid via prepayment credits",
                )
                invoice.amount_paid += credit_amount
                if invoice.amount_paid >= invoice.total_amount:
                    invoice.status = "paid"
                else:
                    invoice.status = "partial"
                invoice.save(update_fields=["amount_paid", "status"])
                return payment, None

            # Call gateway
            result = gateway.create_payment(
                amount=float(remaining),
                currency="usd",
                metadata={
                    "invoice_id": str(invoice.pk),
                    "invoice_number": invoice.invoice_number,
                    "tenant_id": str(invoice.tenant_id),
                },
            )

            if not result.success:
                # Reverse credit application on failure
                if credit_amount > 0:
                    PaymentService._reverse_credits(invoice.tenant, credit_amount)
                raise ValueError(result.error_message or "Gateway payment creation failed.")

            gateway_config_obj = None
            from .models import PaymentGatewayConfig

            if gateway_provider:
                gateway_config_obj = PaymentGatewayConfig.objects.filter(
                    provider=gateway_provider, is_active=True
                ).first()
            else:
                gateway_config_obj = PaymentGatewayConfig.objects.filter(
                    is_default=True, is_active=True
                ).first()

            payment = Payment.objects.create(
                tenant=invoice.tenant,
                invoice=invoice,
                amount=remaining + credit_amount,
                method="online",
                status="pending",
                gateway_config=gateway_config_obj,
                gateway_transaction_id=result.transaction_id or "",
                credit_applied=credit_amount,
            )

            client_config = gateway.get_client_config()
            client_config["transaction_id"] = result.transaction_id
            if result.raw_response:
                client_config.update(result.raw_response)

            return payment, client_config

    @staticmethod
    def record_manual_payment(invoice, amount, method, reference_number="", notes="", recorded_by=None):
        """
        Record a cash/check/money_order/bank_transfer payment.
        Handles overpayment by creating PrepaymentCredit for the excess.
        """
        from .models import Payment, PrepaymentCredit

        with transaction.atomic():
            invoice_locked = type(invoice).objects.select_for_update().get(pk=invoice.pk)

            payment = Payment.objects.create(
                tenant=invoice_locked.tenant,
                invoice=invoice_locked,
                amount=amount,
                method=method,
                status="completed",
                reference_number=reference_number,
                notes=notes,
            )

            invoice_locked.amount_paid += amount

            overpayment = invoice_locked.amount_paid - invoice_locked.total_amount
            if overpayment > Decimal("0.00"):
                PrepaymentCredit.objects.create(
                    tenant=invoice_locked.tenant,
                    amount=overpayment,
                    remaining_amount=overpayment,
                    reason=f"Overpayment on invoice {invoice_locked.invoice_number}",
                    source_payment=payment,
                )
                invoice_locked.status = "paid"
            elif invoice_locked.amount_paid >= invoice_locked.total_amount:
                invoice_locked.status = "paid"
            else:
                invoice_locked.status = "partial"

            invoice_locked.save(update_fields=["amount_paid", "status"])

            # Update the caller's reference
            invoice.amount_paid = invoice_locked.amount_paid
            invoice.status = invoice_locked.status

        return payment

    @staticmethod
    def confirm_gateway_payment(payment_id):
        """
        Verify a payment with the gateway and complete it.
        Called by webhook/callback after gateway confirms.
        """
        from apps.core.services.payments.base import PaymentStatus
        from apps.core.services.payments.factory import get_gateway_for_provider

        from .models import Payment

        with transaction.atomic():
            payment = Payment.objects.select_for_update().select_related(
                "invoice", "gateway_config"
            ).get(pk=payment_id)

            if payment.status != "pending":
                return {"status": payment.status, "message": "Already processed."}

            invoice = payment.invoice

            if payment.gateway_config and payment.gateway_transaction_id:
                gateway = get_gateway_for_provider(payment.gateway_config.provider)
                if gateway:
                    status = gateway.verify_payment(payment.gateway_transaction_id)
                    if status == PaymentStatus.COMPLETED:
                        payment.status = "completed"
                    elif status == PaymentStatus.FAILED:
                        payment.status = "failed"
                        if payment.credit_applied > 0:
                            PaymentService._reverse_credits(
                                payment.tenant, payment.credit_applied
                            )
                        payment.save(update_fields=["status"])
                        return {"status": "failed", "payment_id": str(payment_id)}
                    else:
                        return {"status": "pending", "message": "Payment still processing."}
                else:
                    payment.status = "completed"
            else:
                payment.status = "completed"

            payment.save(update_fields=["status"])

            actual_amount = payment.amount
            invoice.amount_paid += actual_amount
            if invoice.amount_paid >= invoice.total_amount:
                invoice.status = "paid"
            else:
                invoice.status = "partial"
            invoice.save(update_fields=["amount_paid", "status"])

        return {"status": "completed", "payment_id": str(payment_id)}

    @staticmethod
    def _apply_prepayment_credits(invoice):
        """
        Deduct available PrepaymentCredit from invoice balance (FIFO).
        Returns total credit amount applied.
        """
        from .models import PrepaymentCredit

        credits = PrepaymentCredit.objects.filter(
            tenant=invoice.tenant, remaining_amount__gt=0,
        ).order_by("created_at")

        total_applied = Decimal("0.00")
        balance = invoice.balance_due

        for credit in credits:
            if balance <= 0:
                break
            applicable = min(credit.remaining_amount, balance)
            credit.remaining_amount -= applicable
            credit.save(update_fields=["remaining_amount"])
            balance -= applicable
            total_applied += applicable

        return total_applied

    @staticmethod
    def _reverse_credits(tenant, amount):
        """Reverse credit application if a payment fails."""
        from .models import PrepaymentCredit

        PrepaymentCredit.objects.create(
            tenant=tenant,
            amount=amount,
            remaining_amount=amount,
            reason="Reversed: payment failed after credit applied",
        )


class LateFeeService:
    """Late fee and interest application logic."""

    @staticmethod
    def apply_late_fees_for_invoice(invoice):
        """
        Check if an invoice is eligible for a late fee and apply it.
        Uses PropertyBillingConfig from the invoice's property.
        """
        from .models import InvoiceLineItem, LateFeeLog, PropertyBillingConfig

        try:
            config = PropertyBillingConfig.objects.get(
                property=invoice.lease.unit.property,
            )
        except PropertyBillingConfig.DoesNotExist:
            return None

        if not config.late_fee_enabled or config.late_fee_amount <= 0:
            return None

        today = timezone.now().date()
        grace_deadline = invoice.due_date + timedelta(days=config.grace_period_days)

        if today <= grace_deadline:
            return None

        # Check frequency limits
        if config.late_fee_frequency == "one_time":
            if invoice.late_fee_logs.filter(fee_type__in=["flat", "percentage"]).exists():
                return None

        if config.late_fee_frequency == "recurring_monthly":
            current_month_start = today.replace(day=1)
            if invoice.late_fee_logs.filter(
                fee_type__in=["flat", "percentage"],
                applied_date__gte=current_month_start,
            ).exists():
                return None

        # Check cap
        if config.late_fee_cap > 0 and invoice.late_fees_total >= config.late_fee_cap:
            return None

        # Calculate fee
        if config.late_fee_type == "flat":
            fee_amount = config.late_fee_amount
        else:
            fee_amount = (invoice.balance_due * config.late_fee_amount / 100).quantize(
                Decimal("0.01")
            )

        # Enforce cap
        if config.late_fee_cap > 0:
            remaining_cap = config.late_fee_cap - invoice.late_fees_total
            fee_amount = min(fee_amount, remaining_cap)

        if fee_amount <= 0:
            return None

        with transaction.atomic():
            line_item = InvoiceLineItem.objects.create(
                invoice=invoice,
                charge_type="late_fee",
                description=f"Late Fee ({config.get_late_fee_type_display()})",
                quantity=1,
                unit_price=fee_amount,
                amount=fee_amount,
            )
            LateFeeLog.objects.create(
                invoice=invoice,
                line_item=line_item,
                fee_type=config.late_fee_type,
                amount=fee_amount,
                applied_date=today,
            )
            invoice.late_fees_total += fee_amount
            invoice.total_amount += fee_amount
            invoice.save(update_fields=["late_fees_total", "total_amount"])

        return line_item

    @staticmethod
    def apply_interest_for_invoice(invoice):
        """Apply daily-accrued interest based on annual rate."""
        from .models import InvoiceLineItem, LateFeeLog, PropertyBillingConfig

        try:
            config = PropertyBillingConfig.objects.get(
                property=invoice.lease.unit.property,
            )
        except PropertyBillingConfig.DoesNotExist:
            return None

        if not config.interest_enabled or config.annual_interest_rate <= 0:
            return None

        today = timezone.now().date()

        # Only apply if past due
        if today <= invoice.due_date:
            return None

        # Only apply once per day
        if invoice.late_fee_logs.filter(fee_type="interest", applied_date=today).exists():
            return None

        daily_rate = config.annual_interest_rate / 365 / 100
        interest_amount = (invoice.balance_due * daily_rate).quantize(Decimal("0.01"))

        if interest_amount <= 0:
            return None

        with transaction.atomic():
            line_item = InvoiceLineItem.objects.create(
                invoice=invoice,
                charge_type="late_fee",
                description=f"Interest ({config.annual_interest_rate}% APR)",
                quantity=1,
                unit_price=interest_amount,
                amount=interest_amount,
            )
            LateFeeLog.objects.create(
                invoice=invoice,
                line_item=line_item,
                fee_type="interest",
                amount=interest_amount,
                applied_date=today,
            )
            invoice.late_fees_total += interest_amount
            invoice.total_amount += interest_amount
            invoice.save(update_fields=["late_fees_total", "total_amount"])

        return line_item
