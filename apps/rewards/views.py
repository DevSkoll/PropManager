from decimal import Decimal

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.decorators import admin_required, tenant_required
from apps.accounts.models import User
from apps.billing.models import Invoice
from apps.properties.models import Property

from .forms import (
    AdminAdjustBalanceForm,
    ManualRewardGrantForm,
    PropertyRewardsConfigForm,
    StreakRewardTierFormSet,
    TenantApplyRewardsForm,
)
from .models import (
    PropertyRewardsConfig,
    RewardBalance,
    RewardTransaction,
    StreakEvaluation,
)
from .services import RewardService


# ---------------------------------------------------------------------------
# Admin Views
# ---------------------------------------------------------------------------


@admin_required
def admin_property_rewards_list(request):
    """List all properties with their rewards configuration status."""
    properties = Property.objects.filter(is_active=True).order_by("name")

    property_configs = []
    for prop in properties:
        config = PropertyRewardsConfig.objects.filter(property=prop).first()
        property_configs.append({
            "property": prop,
            "config": config,
            "enabled": config.rewards_enabled if config else False,
            "streak_enabled": config.streak_reward_enabled if config else False,
            "prepayment_enabled": config.prepayment_reward_enabled if config else False,
            "auto_apply": config.auto_apply_rewards if config else False,
            "tier_count": config.streak_tiers.count() if config else 0,
        })

    return render(request, "rewards/admin_property_rewards_list.html", {
        "property_configs": property_configs,
    })


@admin_required
def admin_property_rewards_config(request, property_pk):
    """Create/edit PropertyRewardsConfig for a property with streak tier formset."""
    prop = get_object_or_404(Property, pk=property_pk)
    config, created = PropertyRewardsConfig.objects.get_or_create(
        property=prop,
        defaults={
            "rewards_enabled": False,
            "streak_reward_enabled": False,
            "prepayment_reward_enabled": False,
        },
    )

    if request.method == "POST":
        form = PropertyRewardsConfigForm(request.POST, instance=config)
        formset = StreakRewardTierFormSet(request.POST, instance=config)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, f"Rewards configuration for {prop.name} saved.")
            return redirect("rewards_admin:property_rewards_config", property_pk=prop.pk)
    else:
        form = PropertyRewardsConfigForm(instance=config)
        formset = StreakRewardTierFormSet(instance=config)

    context = {
        "property": prop,
        "form": form,
        "formset": formset,
        "config": config,
    }
    return render(request, "rewards/admin_property_rewards_config.html", context)


@admin_required
def admin_grant_reward(request):
    """Admin grants a manual reward to a tenant."""
    if request.method == "POST":
        form = ManualRewardGrantForm(request.POST)
        if form.is_valid():
            tenant = form.cleaned_data["tenant"]
            amount = form.cleaned_data["amount"]
            description = form.cleaned_data["description"]
            RewardService.grant_reward(
                tenant=tenant,
                amount=amount,
                transaction_type="manual_grant",
                description=description,
                granted_by=request.user,
            )
            messages.success(request, f"Granted ${amount} reward to {tenant}.")
            return redirect("rewards_admin:reward_balances")
    else:
        form = ManualRewardGrantForm()

    return render(request, "rewards/admin_grant_reward.html", {"form": form})


@admin_required
def admin_adjust_balance(request, tenant_pk):
    """Admin +/- adjustment to a tenant's reward balance."""
    tenant = get_object_or_404(User, pk=tenant_pk, role="tenant")
    balance = RewardService.get_or_create_balance(tenant)

    if request.method == "POST":
        form = AdminAdjustBalanceForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data["amount"]
            description = form.cleaned_data["description"]
            RewardService.admin_adjust_balance(
                tenant=tenant,
                amount=amount,
                description=description,
                adjusted_by=request.user,
            )
            messages.success(request, f"Balance adjusted by ${amount} for {tenant}.")
            return redirect("rewards_admin:tenant_reward_detail", tenant_pk=tenant.pk)
    else:
        form = AdminAdjustBalanceForm()

    context = {
        "tenant": tenant,
        "balance": balance,
        "form": form,
    }
    return render(request, "rewards/admin_adjust_balance.html", context)


@admin_required
def admin_reward_balances(request):
    """Table of all tenant reward balances."""
    search = request.GET.get("q", "").strip()
    balances = RewardBalance.objects.select_related("tenant").order_by("-balance")

    if search:
        balances = balances.filter(
            Q(tenant__first_name__icontains=search)
            | Q(tenant__last_name__icontains=search)
            | Q(tenant__email__icontains=search)
        )

    context = {
        "balances": balances,
        "search": search,
    }
    return render(request, "rewards/admin_reward_balances.html", context)


@admin_required
def admin_reward_history(request):
    """Filterable reward transaction log."""
    transactions = RewardTransaction.objects.select_related(
        "tenant", "invoice", "streak_tier"
    )

    # Filters
    tenant_pk = request.GET.get("tenant")
    txn_type = request.GET.get("type")
    date_from = request.GET.get("from")
    date_to = request.GET.get("to")

    if tenant_pk:
        transactions = transactions.filter(tenant_id=tenant_pk)
    if txn_type:
        transactions = transactions.filter(transaction_type=txn_type)
    if date_from:
        transactions = transactions.filter(created_at__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(created_at__date__lte=date_to)

    tenants = User.objects.filter(role="tenant").order_by("last_name", "first_name")

    context = {
        "transactions": transactions[:200],
        "tenants": tenants,
        "transaction_types": RewardTransaction.TRANSACTION_TYPE_CHOICES,
        "current_tenant": tenant_pk or "",
        "current_type": txn_type or "",
        "current_from": date_from or "",
        "current_to": date_to or "",
    }
    return render(request, "rewards/admin_reward_history.html", context)


@admin_required
def admin_tenant_reward_detail(request, tenant_pk):
    """Single tenant's reward detail: balance, streak info, transaction history."""
    tenant = get_object_or_404(User, pk=tenant_pk, role="tenant")
    balance = RewardService.get_or_create_balance(tenant)
    transactions = RewardTransaction.objects.filter(tenant=tenant).select_related(
        "invoice", "streak_tier"
    )[:50]
    streak_evals = StreakEvaluation.objects.filter(tenant=tenant).select_related(
        "config__property"
    )

    context = {
        "tenant": tenant,
        "balance": balance,
        "transactions": transactions,
        "streak_evals": streak_evals,
    }
    return render(request, "rewards/admin_tenant_reward_detail.html", context)


# ---------------------------------------------------------------------------
# Tenant Views
# ---------------------------------------------------------------------------


@tenant_required
def tenant_rewards_dashboard(request):
    """Tenant rewards dashboard: balance, streak progress, recent transactions."""
    balance = RewardService.get_or_create_balance(request.user)
    transactions = RewardTransaction.objects.filter(
        tenant=request.user
    ).select_related("invoice", "streak_tier")[:10]

    streak_evals = StreakEvaluation.objects.filter(
        tenant=request.user
    ).select_related("config__property")

    # Outstanding invoices where rewards can be applied
    outstanding_invoices = Invoice.objects.filter(
        tenant=request.user,
        status__in=["issued", "partial", "overdue"],
    ).order_by("due_date")[:5]

    context = {
        "balance": balance,
        "transactions": transactions,
        "streak_evals": streak_evals,
        "outstanding_invoices": outstanding_invoices,
    }
    return render(request, "rewards/tenant_rewards_dashboard.html", context)


@tenant_required
def tenant_apply_rewards(request, invoice_pk):
    """Tenant applies reward balance to a specific invoice."""
    invoice = get_object_or_404(
        Invoice.objects.select_related("lease", "lease__unit"),
        pk=invoice_pk,
        tenant=request.user,
    )

    if invoice.status not in ("issued", "partial", "overdue"):
        messages.error(request, "This invoice cannot have rewards applied.")
        return redirect("billing_tenant:invoice_detail", pk=invoice.pk)

    balance = RewardService.get_or_create_balance(request.user)

    if request.method == "POST":
        form = TenantApplyRewardsForm(request.POST)
        if form.is_valid():
            apply_all = form.cleaned_data.get("apply_all")
            amount = form.cleaned_data.get("amount")

            if apply_all:
                amount = None  # Will apply full balance up to balance_due
            payment = RewardService.apply_rewards_to_invoice(
                invoice=invoice,
                amount=amount,
                applied_by=request.user,
            )
            if payment:
                messages.success(
                    request,
                    f"${payment.reward_applied} reward applied to invoice {invoice.invoice_number}.",
                )
            else:
                messages.warning(request, "No rewards could be applied.")
            return redirect("billing_tenant:invoice_detail", pk=invoice.pk)
    else:
        form = TenantApplyRewardsForm()

    context = {
        "invoice": invoice,
        "balance": balance,
        "form": form,
    }
    return render(request, "rewards/tenant_apply_rewards.html", context)


@tenant_required
def tenant_reward_history(request):
    """Full transaction history for the tenant."""
    transactions = RewardTransaction.objects.filter(
        tenant=request.user
    ).select_related("invoice", "streak_tier")

    context = {
        "transactions": transactions,
    }
    return render(request, "rewards/tenant_reward_history.html", context)
