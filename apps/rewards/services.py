import logging
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class RewardService:
    """Centralized reward granting, redemption, and evaluation logic."""

    @staticmethod
    def get_or_create_balance(tenant):
        """Get or create a RewardBalance for the given tenant."""
        from .models import RewardBalance

        balance, _ = RewardBalance.objects.get_or_create(
            tenant=tenant,
            defaults={"balance": Decimal("0.00"), "total_earned": Decimal("0.00"), "total_redeemed": Decimal("0.00")},
        )
        return balance

    @staticmethod
    def grant_reward(
        tenant,
        amount,
        transaction_type,
        description,
        granted_by=None,
        invoice=None,
        payment=None,
        streak_tier=None,
    ):
        """
        Grant a reward to a tenant. Updates balance and creates audit trail.
        Dispatches a notification to the tenant.

        Returns the RewardTransaction.
        """
        from .models import RewardBalance, RewardTransaction

        if amount <= 0:
            raise ValueError("Reward amount must be positive.")

        with transaction.atomic():
            balance, _ = RewardBalance.objects.select_for_update().get_or_create(
                tenant=tenant,
                defaults={"balance": Decimal("0.00"), "total_earned": Decimal("0.00"), "total_redeemed": Decimal("0.00")},
            )

            balance.balance += amount
            balance.total_earned += amount
            balance.save(update_fields=["balance", "total_earned", "updated_at"])

            txn = RewardTransaction.objects.create(
                tenant=tenant,
                transaction_type=transaction_type,
                amount=amount,
                balance_after=balance.balance,
                description=description,
                invoice=invoice,
                payment=payment,
                streak_tier=streak_tier,
                created_by=granted_by,
            )

        # Dispatch notification outside the transaction
        try:
            from apps.notifications.services import dispatch_event

            dispatch_event("reward_earned", {
                "subject": f"You earned a ${amount} reward!",
                "body": description,
                "tenant_id": str(tenant.pk),
                "notification_category": "rewards",
                "action_url": "/tenant/rewards/",
            })
        except Exception:
            logger.exception("Failed to dispatch reward_earned notification for tenant %s", tenant.pk)

        return txn

    @staticmethod
    def apply_rewards_to_invoice(invoice, amount=None, applied_by=None):
        """
        Apply reward balance to an invoice. Creates a Payment(method="reward")
        and a RewardTransaction(type="redeemed").

        Args:
            invoice: The Invoice to apply rewards to.
            amount: Specific amount to apply. If None, applies full balance up to balance_due.
            applied_by: The user performing the action (for audit).

        Returns the Payment, or None if nothing was applied.
        """
        from apps.billing.models import Payment

        from .models import RewardBalance, RewardTransaction

        with transaction.atomic():
            invoice_locked = type(invoice).objects.select_for_update().get(pk=invoice.pk)

            if invoice_locked.balance_due <= 0:
                return None

            balance, _ = RewardBalance.objects.select_for_update().get_or_create(
                tenant=invoice_locked.tenant,
                defaults={"balance": Decimal("0.00"), "total_earned": Decimal("0.00"), "total_redeemed": Decimal("0.00")},
            )

            if balance.balance <= 0:
                return None

            if amount is not None:
                apply_amount = min(balance.balance, invoice_locked.balance_due, amount)
            else:
                apply_amount = min(balance.balance, invoice_locked.balance_due)

            if apply_amount <= 0:
                return None

            # Create payment record
            payment = Payment.objects.create(
                tenant=invoice_locked.tenant,
                invoice=invoice_locked,
                amount=apply_amount,
                method="reward",
                status="completed",
                reward_applied=apply_amount,
                notes=f"Reward balance applied to invoice {invoice_locked.invoice_number}",
            )

            # Update invoice
            invoice_locked.amount_paid += apply_amount
            if invoice_locked.amount_paid >= invoice_locked.total_amount:
                invoice_locked.status = "paid"
            else:
                invoice_locked.status = "partial"
            invoice_locked.save(update_fields=["amount_paid", "status"])

            # Update reward balance
            balance.balance -= apply_amount
            balance.total_redeemed += apply_amount
            balance.save(update_fields=["balance", "total_redeemed", "updated_at"])

            # Create audit trail
            RewardTransaction.objects.create(
                tenant=invoice_locked.tenant,
                transaction_type="redeemed",
                amount=-apply_amount,
                balance_after=balance.balance,
                description=f"Applied to invoice {invoice_locked.invoice_number}",
                invoice=invoice_locked,
                payment=payment,
                created_by=applied_by,
            )

            # Update caller's reference
            invoice.amount_paid = invoice_locked.amount_paid
            invoice.status = invoice_locked.status

        return payment

    @staticmethod
    def reverse_reward_application(payment):
        """
        Reverse a reward payment. Restores the reward balance.

        Returns the RewardTransaction for the reversal.
        """
        from .models import RewardBalance, RewardTransaction

        if payment.method != "reward":
            raise ValueError("Can only reverse reward-type payments.")

        with transaction.atomic():
            balance = RewardBalance.objects.select_for_update().get(
                tenant=payment.tenant,
            )

            reversal_amount = payment.reward_applied
            balance.balance += reversal_amount
            balance.total_redeemed -= reversal_amount
            balance.save(update_fields=["balance", "total_redeemed", "updated_at"])

            txn = RewardTransaction.objects.create(
                tenant=payment.tenant,
                transaction_type="reversed",
                amount=reversal_amount,
                balance_after=balance.balance,
                description=f"Reversed reward application on invoice {payment.invoice.invoice_number}",
                invoice=payment.invoice,
                payment=payment,
            )

        return txn

    @staticmethod
    def admin_adjust_balance(tenant, amount, description, adjusted_by=None):
        """
        Admin +/- balance adjustment with audit trail.

        Args:
            tenant: The tenant user.
            amount: Positive to add, negative to deduct.
            description: Human-readable reason.
            adjusted_by: The admin user.

        Returns the RewardTransaction.
        """
        from .models import RewardBalance, RewardTransaction

        with transaction.atomic():
            balance, _ = RewardBalance.objects.select_for_update().get_or_create(
                tenant=tenant,
                defaults={"balance": Decimal("0.00"), "total_earned": Decimal("0.00"), "total_redeemed": Decimal("0.00")},
            )

            balance.balance += amount
            if amount > 0:
                balance.total_earned += amount
            balance.save(update_fields=["balance", "total_earned", "updated_at"])

            txn = RewardTransaction.objects.create(
                tenant=tenant,
                transaction_type="admin_adjustment",
                amount=amount,
                balance_after=balance.balance,
                description=description,
                created_by=adjusted_by,
            )

        return txn

    @staticmethod
    def evaluate_streak_rewards(tenant, property_obj):
        """
        Evaluate consecutive on-time payment months for a tenant at a property.
        Grants rewards for qualifying streak tiers.

        Returns list of granted RewardTransactions.
        """
        from apps.billing.models import Invoice

        from .models import PropertyRewardsConfig, StreakEvaluation

        try:
            config = PropertyRewardsConfig.objects.get(
                property=property_obj,
                rewards_enabled=True,
                streak_reward_enabled=True,
            )
        except PropertyRewardsConfig.DoesNotExist:
            return []

        tiers = list(config.streak_tiers.all())
        if not tiers:
            return []

        evaluation, _ = StreakEvaluation.objects.get_or_create(
            tenant=tenant,
            config=config,
            defaults={"current_streak_months": 0, "awarded_tier_ids": []},
        )

        # Determine the range of months to evaluate
        now = timezone.now().date()
        # Last completed month is the previous month
        last_completed_month = (now.replace(day=1) - timedelta(days=1)).replace(day=1)

        if evaluation.last_evaluated_month:
            # Start from the month after the last evaluated month
            start_month = (evaluation.last_evaluated_month + timedelta(days=32)).replace(day=1)
        else:
            # Find the earliest invoice for this tenant at this property
            earliest_invoice = (
                Invoice.objects.filter(
                    tenant=tenant,
                    lease__unit__property=property_obj,
                )
                .order_by("issue_date")
                .first()
            )
            if not earliest_invoice:
                return []
            start_month = earliest_invoice.issue_date.replace(day=1)

        if start_month > last_completed_month:
            return []

        granted = []
        current_month = start_month

        while current_month <= last_completed_month:
            # Find invoices for this month
            month_end = (current_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            month_invoices = Invoice.objects.filter(
                tenant=tenant,
                lease__unit__property=property_obj,
                issue_date__gte=current_month,
                issue_date__lte=month_end,
                status__in=["paid", "partial", "overdue", "issued"],
            )

            paid_on_time = True
            if not month_invoices.exists():
                # No invoice for this month — skip without breaking streak
                current_month = (current_month + timedelta(days=32)).replace(day=1)
                continue

            for inv in month_invoices:
                # Check if paid on or before due date
                completed_payments = inv.payments.filter(status="completed")
                if not completed_payments.exists():
                    paid_on_time = False
                    break
                # Check if the invoice was fully paid by the due date
                if inv.status not in ("paid",):
                    paid_on_time = False
                    break
                last_payment = completed_payments.order_by("-payment_date").first()
                if last_payment and last_payment.payment_date.date() > inv.due_date:
                    paid_on_time = False
                    break

            if paid_on_time:
                evaluation.current_streak_months += 1
            else:
                evaluation.current_streak_months = 0
                evaluation.streak_broken_at = current_month

            evaluation.last_evaluated_month = current_month

            # Check tiers
            for tier in tiers:
                if evaluation.current_streak_months < tier.months_required:
                    continue

                if tier.is_recurring:
                    # Grant every N months
                    expected_grants = evaluation.current_streak_months // tier.months_required
                    already_granted = evaluation.awarded_tier_ids.count(str(tier.pk))
                    grants_due = expected_grants - already_granted
                    for _ in range(grants_due):
                        txn = RewardService.grant_reward(
                            tenant=tenant,
                            amount=tier.reward_amount,
                            transaction_type="streak_earned",
                            description=f"On-time payment streak: {evaluation.current_streak_months} months at {property_obj.name}",
                            streak_tier=tier,
                        )
                        granted.append(txn)
                        evaluation.awarded_tier_ids.append(str(tier.pk))
                else:
                    # One-time grant
                    if str(tier.pk) not in evaluation.awarded_tier_ids:
                        txn = RewardService.grant_reward(
                            tenant=tenant,
                            amount=tier.reward_amount,
                            transaction_type="streak_earned",
                            description=f"On-time payment streak: {evaluation.current_streak_months} months at {property_obj.name}",
                            streak_tier=tier,
                        )
                        granted.append(txn)
                        evaluation.awarded_tier_ids.append(str(tier.pk))

            current_month = (current_month + timedelta(days=32)).replace(day=1)

        evaluation.save()
        return granted

    @staticmethod
    def evaluate_prepayment_rewards(tenant, property_obj, prepayment_amount):
        """
        Track a prepayment and check if any reward thresholds are crossed.

        Args:
            tenant: The tenant user.
            property_obj: The Property instance.
            prepayment_amount: The overpayment amount (Decimal).

        Returns list of granted RewardTransactions.
        """
        from .models import PrepaymentRewardTracker, PropertyRewardsConfig

        try:
            config = PropertyRewardsConfig.objects.get(
                property=property_obj,
                rewards_enabled=True,
                prepayment_reward_enabled=True,
            )
        except PropertyRewardsConfig.DoesNotExist:
            return []

        if config.prepayment_threshold_amount <= 0 or config.prepayment_reward_amount <= 0:
            return []

        tracker, _ = PrepaymentRewardTracker.objects.get_or_create(
            tenant=tenant,
            config=config,
            defaults={"cumulative_prepayment": Decimal("0.00"), "rewards_granted_count": 0},
        )

        tracker.cumulative_prepayment += prepayment_amount

        # How many thresholds have been crossed total?
        thresholds_crossed = int(tracker.cumulative_prepayment // config.prepayment_threshold_amount)
        new_grants = thresholds_crossed - tracker.rewards_granted_count

        granted = []
        for _ in range(new_grants):
            txn = RewardService.grant_reward(
                tenant=tenant,
                amount=config.prepayment_reward_amount,
                transaction_type="prepayment_earned",
                description=f"Prepayment reward at {property_obj.name} (threshold: ${config.prepayment_threshold_amount})",
            )
            granted.append(txn)

        tracker.rewards_granted_count = thresholds_crossed
        tracker.save(update_fields=["cumulative_prepayment", "rewards_granted_count", "updated_at"])

        return granted
