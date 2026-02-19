import csv
from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render

from apps.core.decorators import admin_required


@admin_required
def reports_index(request):
    return render(request, "reports/index.html")


@admin_required
def rent_roll_report(request):
    from apps.leases.models import Lease

    leases = Lease.objects.filter(
        status="active"
    ).select_related("tenant", "unit", "unit__property").order_by(
        "unit__property__name", "unit__unit_number"
    )

    total_rent = leases.aggregate(total=Sum("monthly_rent"))["total"] or 0

    if request.GET.get("format") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="rent_roll_{date.today()}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Property", "Unit", "Tenant", "Monthly Rent", "Lease Start", "Lease End", "Type"])
        for lease in leases:
            writer.writerow([
                lease.unit.property.name,
                lease.unit.unit_number,
                lease.tenant.get_full_name() or lease.tenant.username,
                str(lease.monthly_rent),
                str(lease.start_date),
                str(lease.end_date or "Month-to-Month"),
                lease.get_lease_type_display(),
            ])
        return response

    return render(request, "reports/rent_roll.html", {
        "leases": leases,
        "total_rent": total_rent,
    })


@admin_required
def aging_receivables_report(request):
    from django.utils import timezone
    from apps.billing.models import Invoice

    today = timezone.now().date()
    invoices = Invoice.objects.filter(
        status__in=["issued", "partial", "overdue"]
    ).select_related("tenant", "lease", "lease__unit", "lease__unit__property").order_by("due_date")

    current = []
    days_30 = []
    days_60 = []
    days_90_plus = []

    for inv in invoices:
        balance = inv.total_amount - inv.amount_paid
        days_overdue = (today - inv.due_date).days if inv.due_date <= today else 0
        inv.balance = balance
        inv.days_overdue = days_overdue

        if days_overdue <= 0:
            current.append(inv)
        elif days_overdue <= 30:
            days_30.append(inv)
        elif days_overdue <= 60:
            days_60.append(inv)
        else:
            days_90_plus.append(inv)

    totals = {
        "current": sum(i.balance for i in current),
        "days_30": sum(i.balance for i in days_30),
        "days_60": sum(i.balance for i in days_60),
        "days_90_plus": sum(i.balance for i in days_90_plus),
    }
    totals["grand_total"] = sum(totals.values())

    if request.GET.get("format") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="aging_receivables_{date.today()}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Invoice #", "Tenant", "Property", "Due Date", "Total", "Paid", "Balance", "Days Overdue", "Aging Bucket"])
        for inv in invoices:
            if inv.days_overdue <= 0:
                bucket = "Current"
            elif inv.days_overdue <= 30:
                bucket = "1-30 Days"
            elif inv.days_overdue <= 60:
                bucket = "31-60 Days"
            else:
                bucket = "90+ Days"
            writer.writerow([
                inv.invoice_number, inv.tenant.get_full_name() or inv.tenant.username,
                inv.lease.unit.property.name if inv.lease else "",
                str(inv.due_date), str(inv.total_amount), str(inv.amount_paid),
                str(inv.balance), inv.days_overdue, bucket,
            ])
        return response

    buckets = [
        ("Current", current),
        ("1-30 Days Overdue", days_30),
        ("31-60 Days Overdue", days_60),
        ("90+ Days Overdue", days_90_plus),
    ]

    return render(request, "reports/aging_receivables.html", {
        "current": current,
        "days_30": days_30,
        "days_60": days_60,
        "days_90_plus": days_90_plus,
        "totals": totals,
        "buckets": buckets,
    })


@admin_required
def payment_history_report(request):
    from apps.billing.models import Payment

    payments = Payment.objects.filter(
        status="completed"
    ).select_related("tenant", "invoice").order_by("-payment_date")

    date_from = request.GET.get("from")
    date_to = request.GET.get("to")
    if date_from:
        payments = payments.filter(payment_date__date__gte=date_from)
    if date_to:
        payments = payments.filter(payment_date__date__lte=date_to)

    total = payments.aggregate(total=Sum("amount"))["total"] or 0

    if request.GET.get("format") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="payment_history_{date.today()}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Date", "Tenant", "Invoice #", "Amount", "Method", "Reference"])
        for p in payments:
            writer.writerow([
                str(p.payment_date.date()), p.tenant.get_full_name() or p.tenant.username,
                p.invoice.invoice_number, str(p.amount),
                p.get_method_display(), p.reference_number,
            ])
        return response

    return render(request, "reports/payment_history.html", {
        "payments": payments[:100],
        "total": total,
        "date_from": date_from or "",
        "date_to": date_to or "",
    })


@admin_required
def workorder_summary_report(request):
    from django.db.models import Count, Avg
    from apps.workorders.models import WorkOrder

    work_orders = WorkOrder.objects.all()

    status_summary = work_orders.values("status").annotate(count=Count("id")).order_by("status")
    priority_summary = work_orders.values("priority").annotate(count=Count("id")).order_by("priority")
    category_summary = work_orders.values("category").annotate(count=Count("id")).order_by("-count")

    total_cost = work_orders.filter(
        actual_cost__isnull=False
    ).aggregate(total=Sum("actual_cost"))["total"] or 0

    if request.GET.get("format") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="workorder_summary_{date.today()}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Metric", "Value", "Count"])
        for s in status_summary:
            writer.writerow(["Status", s["status"], s["count"]])
        for p in priority_summary:
            writer.writerow(["Priority", p["priority"], p["count"]])
        for c in category_summary:
            writer.writerow(["Category", c["category"], c["count"]])
        return response

    return render(request, "reports/workorder_summary.html", {
        "status_summary": status_summary,
        "priority_summary": priority_summary,
        "category_summary": category_summary,
        "total_cost": total_cost,
        "total_wo": work_orders.count(),
    })
