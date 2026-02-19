from django.conf import settings
from django.db import models

from apps.core.models import AuditMixin, TimeStampedModel


class PropertyRewardsConfig(TimeStampedModel):
    """Per-property rewards program toggle and settings."""

    property = models.OneToOneField(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="rewards_config",
    )
    rewards_enabled = models.BooleanField(
        default=False,
        help_text="Master toggle for the rewards program on this property.",
    )
    streak_reward_enabled = models.BooleanField(default=False)
    prepayment_reward_enabled = models.BooleanField(default=False)
    prepayment_threshold_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Amount of cumulative prepayment needed to earn a reward.",
    )
    prepayment_reward_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Reward amount granted per threshold reached.",
    )
    auto_apply_rewards = models.BooleanField(
        default=False,
        help_text="Automatically apply tenant reward balances to new invoices.",
    )

    class Meta:
        verbose_name = "Property Rewards Configuration"

    def __str__(self):
        return f"Rewards Config: {self.property.name}"


class StreakRewardTier(TimeStampedModel):
    """Defines a streak milestone and the reward granted upon reaching it."""

    config = models.ForeignKey(
        PropertyRewardsConfig,
        on_delete=models.CASCADE,
        related_name="streak_tiers",
    )
    months_required = models.PositiveIntegerField(
        help_text="Consecutive on-time payment months required.",
    )
    reward_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_recurring = models.BooleanField(
        default=False,
        help_text="If True, re-grants every N months. If False, one-time only.",
    )

    class Meta:
        unique_together = [("config", "months_required")]
        ordering = ["months_required"]

    def __str__(self):
        recur = " (recurring)" if self.is_recurring else ""
        return f"{self.months_required} months → ${self.reward_amount}{recur}"


class RewardBalance(TimeStampedModel):
    """Per-tenant reward wallet. NOT real money — promotional only."""

    tenant = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reward_balance",
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_redeemed = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Reward Balance: {self.tenant} — ${self.balance}"


class RewardTransaction(TimeStampedModel, AuditMixin):
    """Immutable audit trail for every reward balance change."""

    TRANSACTION_TYPE_CHOICES = [
        ("streak_earned", "Streak Earned"),
        ("prepayment_earned", "Prepayment Earned"),
        ("manual_grant", "Manual Grant"),
        ("redeemed", "Redeemed"),
        ("reversed", "Reversed"),
        ("admin_adjustment", "Admin Adjustment"),
        ("expired", "Expired"),
    ]

    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reward_transactions",
    )
    transaction_type = models.CharField(
        max_length=20, choices=TRANSACTION_TYPE_CHOICES, db_index=True
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=500)
    invoice = models.ForeignKey(
        "billing.Invoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reward_transactions",
    )
    payment = models.ForeignKey(
        "billing.Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reward_transactions",
    )
    streak_tier = models.ForeignKey(
        StreakRewardTier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reward_transactions",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        sign = "+" if self.amount >= 0 else ""
        return f"{self.get_transaction_type_display()} {sign}${self.amount} ({self.tenant})"


class StreakEvaluation(TimeStampedModel):
    """Tracks current streak state per tenant per property."""

    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="streak_evaluations",
    )
    config = models.ForeignKey(
        PropertyRewardsConfig,
        on_delete=models.CASCADE,
        related_name="streak_evaluations",
    )
    current_streak_months = models.PositiveIntegerField(default=0)
    last_evaluated_month = models.DateField(
        null=True, blank=True,
        help_text="First day of the last month evaluated.",
    )
    streak_broken_at = models.DateField(null=True, blank=True)
    awarded_tier_ids = models.JSONField(
        default=list,
        help_text="List of StreakRewardTier PKs already awarded (for non-recurring tiers).",
    )

    class Meta:
        unique_together = [("tenant", "config")]

    def __str__(self):
        return f"Streak: {self.tenant} @ {self.config.property.name} — {self.current_streak_months} months"


class PrepaymentRewardTracker(TimeStampedModel):
    """Tracks cumulative prepayments per tenant per property for threshold detection."""

    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="prepayment_reward_trackers",
    )
    config = models.ForeignKey(
        PropertyRewardsConfig,
        on_delete=models.CASCADE,
        related_name="prepayment_trackers",
    )
    cumulative_prepayment = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    rewards_granted_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("tenant", "config")]

    def __str__(self):
        return (
            f"Prepayment Tracker: {self.tenant} @ {self.config.property.name} "
            f"— ${self.cumulative_prepayment}"
        )
