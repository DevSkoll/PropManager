"""
Django-Q2 async tasks for the rewards app.

Schedule these via Django-Q2 admin or programmatically:
    async_task('apps.rewards.tasks.evaluate_all_streak_rewards')
    async_task('apps.rewards.tasks.auto_apply_rewards_to_invoices')
"""

import logging

logger = logging.getLogger(__name__)


def evaluate_all_streak_rewards():
    """
    Monthly task (run on the 2nd of each month, after invoice generation).
    Iterates all reward-enabled properties and active tenants,
    evaluating streak rewards for each.

    Returns:
        dict with evaluated and granted counts.
    """
    from apps.leases.models import Lease

    from .models import PropertyRewardsConfig
    from .services import RewardService

    configs = PropertyRewardsConfig.objects.filter(
        rewards_enabled=True,
        streak_reward_enabled=True,
        property__is_active=True,
    ).select_related("property")

    results = {"evaluated": 0, "granted": 0, "errors": []}

    for config in configs:
        active_leases = Lease.objects.filter(
            unit__property=config.property,
            status="active",
        ).select_related("tenant")

        for lease in active_leases:
            try:
                granted = RewardService.evaluate_streak_rewards(
                    tenant=lease.tenant,
                    property_obj=config.property,
                )
                results["evaluated"] += 1
                results["granted"] += len(granted)
            except Exception as e:
                logger.exception(
                    "Error evaluating streak rewards for tenant %s at property %s",
                    lease.tenant.pk,
                    config.property.pk,
                )
                results["errors"].append(str(e))

    logger.info(
        "evaluate_all_streak_rewards: %d evaluated, %d granted, %d errors.",
        results["evaluated"],
        results["granted"],
        len(results["errors"]),
    )
    return results


def auto_apply_rewards_to_invoices():
    """
    Daily task: for properties with auto_apply_rewards=True,
    apply tenant reward balances to outstanding issued invoices.

    Run after auto_apply_prepayment_credits in the daily task chain.

    Returns:
        dict with applied count.
    """
    from apps.billing.models import Invoice

    from .models import PropertyRewardsConfig, RewardBalance
    from .services import RewardService

    configs = PropertyRewardsConfig.objects.filter(
        rewards_enabled=True,
        auto_apply_rewards=True,
        property__is_active=True,
    ).select_related("property")

    # Collect property IDs with auto-apply enabled
    auto_apply_property_ids = set(configs.values_list("property_id", flat=True))

    if not auto_apply_property_ids:
        logger.info("auto_apply_rewards_to_invoices: no properties with auto-apply enabled.")
        return {"applied": 0}

    # Find tenants with reward balances > 0
    tenants_with_balance = RewardBalance.objects.filter(
        balance__gt=0,
    ).values_list("tenant_id", flat=True)

    # Find outstanding invoices at auto-apply properties for tenants with balances
    invoices = Invoice.objects.filter(
        status__in=["issued", "partial", "overdue"],
        tenant_id__in=tenants_with_balance,
        lease__unit__property_id__in=auto_apply_property_ids,
    ).select_related("tenant", "lease__unit__property").order_by("due_date")

    applied_count = 0
    for invoice in invoices:
        try:
            payment = RewardService.apply_rewards_to_invoice(invoice)
            if payment:
                applied_count += 1
        except Exception:
            logger.exception(
                "Error auto-applying rewards to invoice %s", invoice.pk
            )

    logger.info("auto_apply_rewards_to_invoices: %d rewards applied.", applied_count)
    return {"applied": applied_count}
