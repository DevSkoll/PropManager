"""
Dashboard utility functions for PropManager analytics.

Provides metric calculations, chart data preparation, and trend analysis
for the admin analytics dashboard.
"""

import json
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, F, Q, Sum
from django.db.models.functions import Coalesce, TruncDate, TruncWeek
from django.utils import timezone


def get_financial_metrics(start_date, end_date, property_ids=None):
    """
    Calculate financial KPIs for the given time range.

    Returns:
        dict with total_revenue, expected_revenue, collection_rate,
        late_fees_collected, outstanding_balance
    """
    from apps.billing.models import Invoice, Payment

    # Build property filter
    payment_filters = Q(
        payment_date__date__gte=start_date, payment_date__date__lte=end_date
    )
    if property_ids:
        payment_filters &= Q(invoice__lease__unit__property_id__in=property_ids)

    # Total Revenue (completed payments in period)
    total_revenue = (
        Payment.objects.filter(payment_filters, status="completed").aggregate(
            total=Coalesce(Sum("amount"), Decimal("0"))
        )["total"]
        or Decimal("0")
    )

    # Expected Revenue (invoices issued in period)
    invoice_filters = Q(issue_date__gte=start_date, issue_date__lte=end_date)
    if property_ids:
        invoice_filters &= Q(lease__unit__property_id__in=property_ids)

    expected_revenue = (
        Invoice.objects.filter(
            invoice_filters, status__in=["issued", "paid", "partial", "overdue"]
        ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0")))["total"]
        or Decimal("0")
    )

    # Collection Rate
    if expected_revenue > 0:
        collection_rate = float(total_revenue / expected_revenue * 100)
    else:
        collection_rate = 100.0

    # Late Fees Collected (from LateFeeLog in period)
    from apps.billing.models import LateFeeLog

    late_fee_filters = Q(applied_date__gte=start_date, applied_date__lte=end_date)
    if property_ids:
        late_fee_filters &= Q(invoice__lease__unit__property_id__in=property_ids)

    late_fees_collected = (
        LateFeeLog.objects.filter(late_fee_filters).aggregate(
            total=Coalesce(Sum("amount"), Decimal("0"))
        )["total"]
        or Decimal("0")
    )

    # Outstanding Balance (current, not time-bounded)
    outstanding_filters = Q(status__in=["issued", "partial", "overdue"])
    if property_ids:
        outstanding_filters &= Q(lease__unit__property_id__in=property_ids)

    outstanding = Invoice.objects.filter(outstanding_filters).aggregate(
        total=Coalesce(Sum("total_amount"), Decimal("0")),
        paid=Coalesce(Sum("amount_paid"), Decimal("0")),
    )
    outstanding_balance = (outstanding["total"] or Decimal("0")) - (
        outstanding["paid"] or Decimal("0")
    )

    # Overdue count
    overdue_count = Invoice.objects.filter(
        outstanding_filters, status="overdue"
    ).count()

    return {
        "total_revenue": total_revenue,
        "expected_revenue": expected_revenue,
        "collection_rate": round(collection_rate, 1),
        "late_fees_collected": late_fees_collected,
        "outstanding_balance": outstanding_balance,
        "overdue_count": overdue_count,
    }


def calculate_trend(current_value, previous_value):
    """Calculate percentage change between periods."""
    try:
        current = float(current_value) if current_value else 0
        previous = float(previous_value) if previous_value else 0
    except (TypeError, ValueError):
        return 0

    if previous == 0:
        return 0 if current == 0 else 100
    return round(((current - previous) / previous) * 100, 1)


def get_period_comparison(current_start, current_end, property_ids=None):
    """
    Get metrics for current period and calculate trends vs previous period.

    Returns:
        dict with current metrics, previous metrics, and trend percentages
    """
    period_length = (current_end - current_start).days
    previous_start = current_start - timedelta(days=period_length + 1)
    previous_end = current_start - timedelta(days=1)

    current_metrics = get_financial_metrics(current_start, current_end, property_ids)
    previous_metrics = get_financial_metrics(previous_start, previous_end, property_ids)

    return {
        "current": current_metrics,
        "previous": previous_metrics,
        "revenue_trend": calculate_trend(
            current_metrics["total_revenue"], previous_metrics["total_revenue"]
        ),
        "collection_trend": calculate_trend(
            current_metrics["collection_rate"], previous_metrics["collection_rate"]
        ),
    }


def get_workorder_metrics(start_date, end_date, property_ids=None):
    """
    Calculate work order operational metrics.

    Returns:
        dict with counts by status/priority/category, avg resolution,
        emergency count, completion rate
    """
    from apps.workorders.models import WorkOrder

    filters = Q(created_at__date__gte=start_date, created_at__date__lte=end_date)
    if property_ids:
        filters &= Q(unit__property_id__in=property_ids)

    work_orders = WorkOrder.objects.filter(filters)

    # Count by status
    status_counts = dict(
        work_orders.values("status").annotate(count=Count("id")).values_list("status", "count")
    )

    # Count by priority
    priority_counts = dict(
        work_orders.values("priority").annotate(count=Count("id")).values_list("priority", "count")
    )

    # Count by category (top 8)
    category_counts = list(
        work_orders.values("category")
        .annotate(count=Count("id"))
        .order_by("-count")[:8]
    )

    # Total and completed counts
    total_in_period = work_orders.count()
    completed_in_period = work_orders.filter(
        status__in=["completed", "closed"]
    ).count()

    # Average resolution time (days from created to completed)
    completed_with_dates = work_orders.filter(
        completed_date__isnull=False
    )

    avg_resolution_days = None
    if completed_with_dates.exists():
        # Calculate average manually since we can't subtract dates easily in ORM
        total_days = 0
        count = 0
        for wo in completed_with_dates:
            if wo.completed_date and wo.created_at:
                days = (wo.completed_date - wo.created_at.date()).days
                if days >= 0:
                    total_days += days
                    count += 1
        if count > 0:
            avg_resolution_days = round(total_days / count, 1)

    # Currently open by priority (not filtered by date)
    open_filters = ~Q(status__in=["completed", "closed"])
    if property_ids:
        open_filters &= Q(unit__property_id__in=property_ids)

    open_by_priority = dict(
        WorkOrder.objects.filter(open_filters)
        .values("priority")
        .annotate(count=Count("id"))
        .values_list("priority", "count")
    )

    # Emergency work orders currently open
    emergency_open = WorkOrder.objects.filter(
        open_filters, priority="emergency"
    ).count()

    # Total open
    total_open = WorkOrder.objects.filter(open_filters).count()

    return {
        "status_counts": status_counts,
        "priority_counts": priority_counts,
        "category_counts": category_counts,
        "avg_resolution_days": avg_resolution_days,
        "open_by_priority": open_by_priority,
        "emergency_open": emergency_open,
        "total_open": total_open,
        "total_in_period": total_in_period,
        "completed_in_period": completed_in_period,
    }


def get_lease_metrics(property_ids=None):
    """
    Calculate lease pipeline and expiration metrics.

    Returns:
        dict with pending signatures, expiring counts, month-to-month, totals
    """
    from apps.leases.models import Lease

    today = timezone.now().date()

    filters = Q(status="active")
    if property_ids:
        filters &= Q(unit__property_id__in=property_ids)

    active_leases = Lease.objects.filter(filters)

    # Signature status breakdown
    pending_filters = Q(signature_status__in=["pending", "partial"])
    if property_ids:
        pending_filters &= Q(unit__property_id__in=property_ids)
    pending_signatures = Lease.objects.filter(pending_filters).count()

    # Expiring leases by timeframe
    expiring_30 = active_leases.filter(
        end_date__lte=today + timedelta(days=30), end_date__gte=today
    ).count()

    expiring_60 = active_leases.filter(
        end_date__lte=today + timedelta(days=60), end_date__gt=today + timedelta(days=30)
    ).count()

    expiring_90 = active_leases.filter(
        end_date__lte=today + timedelta(days=90), end_date__gt=today + timedelta(days=60)
    ).count()

    # Month-to-month leases
    month_to_month = active_leases.filter(lease_type="month_to_month").count()

    # Total active leases
    total_active = active_leases.count()

    return {
        "pending_signatures": pending_signatures,
        "expiring_30": expiring_30,
        "expiring_60": expiring_60,
        "expiring_90": expiring_90,
        "month_to_month": month_to_month,
        "total_active": total_active,
    }


def get_tenant_health_metrics(start_date, end_date, property_ids=None):
    """
    Analyze tenant payment behavior and engagement.

    Returns:
        dict with on_time_rate, avg_days_to_payment, method_breakdown,
        reward metrics, streak info
    """
    from apps.billing.models import Payment

    filters = Q(
        payment_date__date__gte=start_date,
        payment_date__date__lte=end_date,
        status="completed",
    )
    if property_ids:
        filters &= Q(invoice__lease__unit__property_id__in=property_ids)

    payments = Payment.objects.filter(filters).select_related("invoice")

    # Payment method breakdown
    method_breakdown = list(
        payments.values("method")
        .annotate(count=Count("id"), total=Sum("amount"))
        .order_by("-total")
    )

    # On-time payment rate
    total_payments = payments.count()
    on_time_count = 0
    total_days_to_pay = 0

    for payment in payments:
        if payment.invoice and payment.invoice.due_date:
            if payment.payment_date.date() <= payment.invoice.due_date:
                on_time_count += 1
            # Days from issue to payment
            if payment.invoice.issue_date:
                days = (payment.payment_date.date() - payment.invoice.issue_date).days
                if days >= 0:
                    total_days_to_pay += days

    on_time_rate = (
        round(on_time_count / total_payments * 100, 1) if total_payments > 0 else 100.0
    )
    avg_days_to_payment = (
        round(total_days_to_pay / total_payments, 1) if total_payments > 0 else None
    )

    # Reward program engagement
    try:
        from apps.rewards.models import RewardBalance, StreakEvaluation

        reward_filters = Q()
        if property_ids:
            # Filter by tenant's active lease property
            from apps.leases.models import Lease
            tenant_ids = Lease.objects.filter(
                status="active", unit__property_id__in=property_ids
            ).values_list("tenant_id", flat=True)
            reward_filters = Q(tenant_id__in=tenant_ids)

        reward_data = RewardBalance.objects.filter(reward_filters).aggregate(
            total_balance=Coalesce(Sum("balance"), Decimal("0")),
            total_earned=Coalesce(Sum("total_earned"), Decimal("0")),
            total_redeemed=Coalesce(Sum("total_redeemed"), Decimal("0")),
            active_count=Count("id", filter=Q(balance__gt=0)),
        )

        # Average streak
        avg_streak = (
            StreakEvaluation.objects.aggregate(avg=Avg("current_streak_months"))["avg"]
            or 0
        )
    except Exception:
        reward_data = {
            "total_balance": Decimal("0"),
            "total_earned": Decimal("0"),
            "total_redeemed": Decimal("0"),
            "active_count": 0,
        }
        avg_streak = 0

    return {
        "method_breakdown": method_breakdown,
        "on_time_rate": on_time_rate,
        "avg_days_to_payment": avg_days_to_payment,
        "total_payments": total_payments,
        "reward_total_balance": reward_data["total_balance"],
        "reward_total_earned": reward_data["total_earned"],
        "reward_active_tenants": reward_data["active_count"],
        "avg_payment_streak": round(avg_streak, 1) if avg_streak else 0,
    }


def get_aging_receivables(property_ids=None):
    """
    Calculate aging buckets for receivables.

    Returns:
        dict with buckets (current, 1_30, 31_60, 61_90, 90_plus),
        each containing total, count, and sample invoices
    """
    from apps.billing.models import Invoice

    today = timezone.now().date()

    filters = Q(status__in=["issued", "partial", "overdue"])
    if property_ids:
        filters &= Q(lease__unit__property_id__in=property_ids)

    invoices = Invoice.objects.filter(filters).select_related(
        "tenant", "lease__unit__property"
    )

    buckets = {
        "current": {"total": Decimal("0"), "count": 0, "invoices": []},
        "1_30": {"total": Decimal("0"), "count": 0, "invoices": []},
        "31_60": {"total": Decimal("0"), "count": 0, "invoices": []},
        "61_90": {"total": Decimal("0"), "count": 0, "invoices": []},
        "90_plus": {"total": Decimal("0"), "count": 0, "invoices": []},
    }

    for inv in invoices:
        balance = inv.total_amount - inv.amount_paid
        if balance <= 0:
            continue

        days_overdue = (today - inv.due_date).days if inv.due_date < today else 0

        if days_overdue <= 0:
            bucket = "current"
        elif days_overdue <= 30:
            bucket = "1_30"
        elif days_overdue <= 60:
            bucket = "31_60"
        elif days_overdue <= 90:
            bucket = "61_90"
        else:
            bucket = "90_plus"

        buckets[bucket]["total"] += balance
        buckets[bucket]["count"] += 1

        # Keep top 5 per bucket for drill-down
        if len(buckets[bucket]["invoices"]) < 5:
            tenant_name = ""
            if inv.tenant:
                tenant_name = inv.tenant.get_full_name() or inv.tenant.username
            buckets[bucket]["invoices"].append(
                {
                    "invoice_number": inv.invoice_number,
                    "tenant": tenant_name,
                    "balance": float(balance),
                    "days_overdue": days_overdue,
                }
            )

    return buckets


def get_revenue_chart_data(start_date, end_date, property_ids=None):
    """
    Prepare revenue data for Chart.js line chart.

    Returns:
        dict with labels and datasets for Chart.js
    """
    from apps.billing.models import Payment

    filters = Q(
        payment_date__date__gte=start_date,
        payment_date__date__lte=end_date,
        status="completed",
    )
    if property_ids:
        filters &= Q(invoice__lease__unit__property_id__in=property_ids)

    period_days = (end_date - start_date).days

    if period_days <= 31:
        # Daily aggregation for shorter periods
        data = (
            Payment.objects.filter(filters)
            .annotate(date=TruncDate("payment_date"))
            .values("date")
            .annotate(amount=Sum("amount"))
            .order_by("date")
        )
        labels = [d["date"].strftime("%b %d") for d in data]
    else:
        # Weekly aggregation for longer periods
        data = (
            Payment.objects.filter(filters)
            .annotate(week=TruncWeek("payment_date"))
            .values("week")
            .annotate(amount=Sum("amount"))
            .order_by("week")
        )
        labels = [d["week"].strftime("%b %d") for d in data]

    values = [float(d["amount"]) for d in data]

    return {
        "labels": labels,
        "datasets": [
            {
                "label": "Revenue Collected",
                "data": values,
                "borderColor": "#198754",
                "backgroundColor": "rgba(25, 135, 84, 0.1)",
                "fill": True,
                "tension": 0.3,
            }
        ],
    }


def get_workorder_charts_data(start_date, end_date, property_ids=None):
    """
    Prepare work order data for Chart.js visualizations.

    Returns:
        dict with priority_chart and category_chart data
    """
    from apps.workorders.models import WorkOrder

    # Currently open work orders by priority (for doughnut)
    open_filters = ~Q(status__in=["completed", "closed"])
    if property_ids:
        open_filters &= Q(unit__property_id__in=property_ids)

    priority_data = list(
        WorkOrder.objects.filter(open_filters)
        .values("priority")
        .annotate(count=Count("id"))
    )

    priority_labels = {
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "emergency": "Emergency",
    }
    priority_colors = {
        "low": "#0dcaf0",
        "medium": "#ffc107",
        "high": "#fd7e14",
        "emergency": "#dc3545",
    }

    priority_chart = {
        "labels": [priority_labels.get(d["priority"], d["priority"]) for d in priority_data],
        "datasets": [
            {
                "data": [d["count"] for d in priority_data],
                "backgroundColor": [
                    priority_colors.get(d["priority"], "#6c757d") for d in priority_data
                ],
            }
        ],
    }

    # Work orders by category in period (for horizontal bar)
    period_filters = Q(created_at__date__gte=start_date, created_at__date__lte=end_date)
    if property_ids:
        period_filters &= Q(unit__property_id__in=property_ids)

    category_data = list(
        WorkOrder.objects.filter(period_filters)
        .values("category")
        .annotate(count=Count("id"))
        .order_by("-count")[:8]
    )

    category_labels = {
        "plumbing": "Plumbing",
        "electrical": "Electrical",
        "hvac": "HVAC",
        "appliance": "Appliance",
        "structural": "Structural",
        "pest_control": "Pest Control",
        "landscaping": "Landscaping",
        "cleaning": "Cleaning",
        "general": "General",
        "other": "Other",
    }

    category_chart = {
        "labels": [category_labels.get(d["category"], d["category"]) for d in category_data],
        "datasets": [
            {
                "label": "Work Orders",
                "data": [d["count"] for d in category_data],
                "backgroundColor": "#0d6efd",
            }
        ],
    }

    return {
        "priority_chart": priority_chart,
        "category_chart": category_chart,
    }


def get_payment_methods_chart_data(method_breakdown):
    """
    Prepare payment methods data for Chart.js pie chart.

    Args:
        method_breakdown: list of dicts with method, count, total

    Returns:
        dict with labels and datasets for Chart.js
    """
    method_labels = {
        "online": "Online",
        "check": "Check",
        "cash": "Cash",
        "money_order": "Money Order",
        "bank_transfer": "Bank Transfer",
        "ach": "ACH",
        "crypto": "Crypto",
        "credit": "Credit Card",
        "reward": "Reward",
    }

    colors = [
        "#0d6efd",
        "#198754",
        "#ffc107",
        "#0dcaf0",
        "#6c757d",
        "#dc3545",
        "#fd7e14",
        "#6610f2",
        "#d63384",
    ]

    return {
        "labels": [
            method_labels.get(m["method"], m["method"]) for m in method_breakdown
        ],
        "datasets": [
            {
                "data": [float(m["total"]) for m in method_breakdown],
                "backgroundColor": colors[: len(method_breakdown)],
            }
        ],
    }
