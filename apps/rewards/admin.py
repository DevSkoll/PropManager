from django.contrib import admin

from .models import (
    PrepaymentRewardTracker,
    PropertyRewardsConfig,
    RewardBalance,
    RewardTransaction,
    StreakEvaluation,
    StreakRewardTier,
)


class StreakRewardTierInline(admin.TabularInline):
    model = StreakRewardTier
    extra = 1


@admin.register(PropertyRewardsConfig)
class PropertyRewardsConfigAdmin(admin.ModelAdmin):
    list_display = [
        "property",
        "rewards_enabled",
        "streak_reward_enabled",
        "prepayment_reward_enabled",
        "auto_apply_rewards",
    ]
    list_filter = ["rewards_enabled", "streak_reward_enabled", "prepayment_reward_enabled"]
    inlines = [StreakRewardTierInline]


@admin.register(StreakRewardTier)
class StreakRewardTierAdmin(admin.ModelAdmin):
    list_display = ["config", "months_required", "reward_amount", "is_recurring"]
    list_filter = ["is_recurring"]


@admin.register(RewardBalance)
class RewardBalanceAdmin(admin.ModelAdmin):
    list_display = ["tenant", "balance", "total_earned", "total_redeemed"]
    readonly_fields = ["balance", "total_earned", "total_redeemed"]
    search_fields = ["tenant__first_name", "tenant__last_name", "tenant__email"]


@admin.register(RewardTransaction)
class RewardTransactionAdmin(admin.ModelAdmin):
    list_display = [
        "tenant",
        "transaction_type",
        "amount",
        "balance_after",
        "created_at",
    ]
    list_filter = ["transaction_type"]
    readonly_fields = [
        "tenant",
        "transaction_type",
        "amount",
        "balance_after",
        "description",
        "invoice",
        "payment",
        "streak_tier",
        "created_by",
        "updated_by",
    ]
    search_fields = ["tenant__first_name", "tenant__last_name", "tenant__email"]


@admin.register(StreakEvaluation)
class StreakEvaluationAdmin(admin.ModelAdmin):
    list_display = [
        "tenant",
        "config",
        "current_streak_months",
        "last_evaluated_month",
    ]
    search_fields = ["tenant__first_name", "tenant__last_name"]


@admin.register(PrepaymentRewardTracker)
class PrepaymentRewardTrackerAdmin(admin.ModelAdmin):
    list_display = [
        "tenant",
        "config",
        "cumulative_prepayment",
        "rewards_granted_count",
    ]
    search_fields = ["tenant__first_name", "tenant__last_name"]
