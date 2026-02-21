from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.core.decorators import admin_required, tenant_required

from .forms import AdminLoginForm, OTPVerifyForm, TenantLoginForm, TenantProfileForm
from .models import OTPToken
from .services import (
    archive_tenant,
    can_delete_tenant,
    delete_tenant,
    get_delete_blockers,
    get_delete_summary,
    restore_tenant,
)

User = get_user_model()


# --- Tenant Passwordless Login ---

def tenant_login(request):
    if request.user.is_authenticated and request.user.is_tenant:
        return redirect("accounts_tenant:tenant_dashboard")

    form = TenantLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        identifier = form.cleaned_data["identifier"].strip()

        user = User.objects.filter(
            Q(email__iexact=identifier) | Q(phone_number=identifier),
            role="tenant",
            is_active=True,
        ).first()

        if not user:
            messages.error(request, "No account found with that email or phone number.")
            return render(request, "tenant/login.html", {"form": form})

        # Rate limiting: check OTP requests in the last hour
        one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
        recent_count = OTPToken.objects.filter(
            user=user, created_at__gte=one_hour_ago
        ).count()

        from django.conf import settings
        if recent_count >= settings.OTP_MAX_REQUESTS_PER_HOUR:
            messages.error(request, "Too many verification requests. Please try again later.")
            return render(request, "tenant/login.html", {"form": form})

        # Determine delivery method
        delivery_method = user.preferred_contact
        if delivery_method == "sms" and not user.phone_number:
            delivery_method = "email"

        # Generate and send OTP
        otp = OTPToken.generate(user=user, purpose="login", delivery_method=delivery_method)
        _send_otp(otp, user)

        request.session["otp_user_id"] = str(user.pk)
        request.session["otp_delivery_method"] = delivery_method
        return redirect("accounts_tenant:tenant_otp_verify")

    return render(request, "tenant/login.html", {"form": form})


def tenant_otp_verify(request):
    user_id = request.session.get("otp_user_id")
    if not user_id:
        return redirect("accounts_tenant:tenant_login")

    delivery_method = request.session.get("otp_delivery_method", "email")
    form = OTPVerifyForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        code = form.cleaned_data["code"]
        user = authenticate(request, user_id=user_id, otp_code=code)
        if user:
            login(request, user, backend="apps.accounts.backends.PasswordlessOTPBackend")
            request.session.pop("otp_user_id", None)
            request.session.pop("otp_delivery_method", None)
            next_url = request.GET.get("next", "")
            # Validate redirect URL to prevent open redirect attacks
            if not next_url or not url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                next_url = "accounts_tenant:tenant_dashboard"
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            return redirect(next_url)
        else:
            messages.error(request, "Invalid or expired code. Please try again.")

    return render(request, "tenant/otp_verify.html", {
        "form": form,
        "delivery_method": delivery_method,
    })


@tenant_required
def tenant_dashboard(request):
    from django.db.models import Sum
    from apps.billing.models import Invoice
    from apps.workorders.models import WorkOrder
    from apps.communications.models import Message, Notification, Announcement
    from apps.weather.models import WeatherAlert

    # Balance
    invoices_owed = Invoice.objects.filter(
        tenant=request.user, status__in=["issued", "partial", "overdue"]
    )
    balance_due = invoices_owed.aggregate(
        total=Sum("total_amount"), paid=Sum("amount_paid")
    )
    total = (balance_due["total"] or 0) - (balance_due["paid"] or 0)

    # Work orders
    open_wo_count = WorkOrder.objects.filter(
        reported_by=request.user
    ).exclude(status__in=["completed", "closed"]).count()

    # Unread messages
    unread_count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    # Weather alerts (for properties where tenant has active lease)
    from apps.leases.models import Lease
    active_leases = Lease.objects.filter(tenant=request.user, status="active")
    property_ids = active_leases.values_list("unit__property_id", flat=True)
    weather_alert_count = WeatherAlert.objects.filter(
        property_id__in=property_ids,
        created_at__gte=timezone.now() - timezone.timedelta(days=7),
    ).count()

    # Get active lease with related unit/property for address display
    active_lease = Lease.objects.filter(
        tenant=request.user, status="active"
    ).select_related("unit__property").first()

    # Get rewards balance and streak
    from apps.rewards.models import RewardBalance, StreakEvaluation
    reward_balance = RewardBalance.objects.filter(tenant=request.user).first()
    streak_info = None
    if active_lease:
        streak_info = StreakEvaluation.objects.filter(
            tenant=request.user,
            config__property=active_lease.unit.property
        ).first()

    # Recent invoices and announcements
    recent_invoices = Invoice.objects.filter(tenant=request.user).order_by("-issue_date")[:5]
    announcements = Announcement.objects.filter(
        is_published=True
    ).filter(
        Q(property__in=property_ids) | Q(property__isnull=True)
    ).order_by("-published_at")[:5]

    return render(request, "tenant/dashboard.html", {
        "balance_due": total,
        "open_wo_count": open_wo_count,
        "unread_count": unread_count,
        "weather_alert_count": weather_alert_count,
        "recent_invoices": recent_invoices,
        "announcements": announcements,
        "active_lease": active_lease,
        "reward_balance": reward_balance,
        "streak_info": streak_info,
    })


@tenant_required
def tenant_profile(request):
    from .models import TenantProfile
    profile, _ = TenantProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = TenantProfileForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            # Update user fields
            request.user.first_name = form.cleaned_data.get("first_name", request.user.first_name)
            request.user.last_name = form.cleaned_data.get("last_name", request.user.last_name)
            request.user.phone_number = form.cleaned_data.get("phone_number", request.user.phone_number)
            request.user.preferred_contact = form.cleaned_data.get("preferred_contact", request.user.preferred_contact)
            request.user.save(update_fields=["first_name", "last_name", "phone_number", "preferred_contact"])
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts_tenant:tenant_profile")
    else:
        form = TenantProfileForm(instance=profile, user=request.user)

    return render(request, "tenant/profile.html", {"form": form, "profile": profile})


# --- Admin Login with OTP ---

def admin_login(request):
    if request.user.is_authenticated and request.user.is_admin_user:
        return redirect("accounts_admin:admin_dashboard")

    form = AdminLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]

        user = authenticate(request, username=username, password=password)
        if user and user.is_admin_user:
            # Check if OTP is required
            admin_profile = getattr(user, "admin_profile", None)
            if admin_profile and admin_profile.otp_enabled:
                otp = OTPToken.generate(
                    user=user, purpose="2fa", delivery_method=admin_profile.otp_delivery
                )
                _send_otp(otp, user)
                request.session["admin_otp_user_id"] = str(user.pk)
                request.session["admin_otp_delivery"] = admin_profile.otp_delivery
                return redirect("accounts_admin:admin_otp_verify")
            else:
                login(request, user)
                messages.success(request, f"Welcome, {user.get_full_name() or user.username}!")
                return redirect("accounts_admin:admin_dashboard")
        else:
            messages.error(request, "Invalid credentials or insufficient permissions.")

    return render(request, "admin_portal/login.html", {"form": form})


def admin_otp_verify(request):
    user_id = request.session.get("admin_otp_user_id")
    if not user_id:
        return redirect("accounts_admin:admin_login")

    delivery_method = request.session.get("admin_otp_delivery", "email")
    form = OTPVerifyForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        code = form.cleaned_data["code"]
        user = authenticate(request, user_id=user_id, otp_code=code)
        if user:
            login(request, user, backend="apps.accounts.backends.PasswordlessOTPBackend")
            request.session.pop("admin_otp_user_id", None)
            request.session.pop("admin_otp_delivery", None)
            messages.success(request, f"Welcome, {user.get_full_name() or user.username}!")
            return redirect("accounts_admin:admin_dashboard")
        else:
            messages.error(request, "Invalid or expired code. Please try again.")

    return render(request, "admin_portal/otp_verify.html", {
        "form": form,
        "delivery_method": delivery_method,
    })


@admin_required
def admin_dashboard(request):
    """
    Modern app launcher dashboard with mini KPIs and searchable app grid.
    """
    from decimal import Decimal

    from django.db.models import Sum
    from django.db.models.functions import Coalesce

    from apps.billing.models import Invoice, Payment
    from apps.core.dashboard_data import CATEGORY_INFO, get_app_tiles
    from apps.properties.models import Unit
    from apps.workorders.models import WorkOrder

    today = timezone.now().date()
    month_start = today.replace(day=1)

    # MINI KPIs (4 key metrics only)
    # Revenue this month
    month_revenue = Payment.objects.filter(
        status="completed",
        payment_date__date__gte=month_start,
        payment_date__date__lte=today,
    ).aggregate(total=Coalesce(Sum("amount"), Decimal("0")))["total"]

    # Outstanding balance
    outstanding = Invoice.objects.filter(
        status__in=["issued", "partial", "overdue"]
    ).aggregate(
        total=Coalesce(Sum("total_amount"), Decimal("0")),
        paid=Coalesce(Sum("amount_paid"), Decimal("0")),
    )
    outstanding_balance = outstanding["total"] - outstanding["paid"]

    # Occupancy
    total_units = Unit.objects.count()
    occupied_units = Unit.objects.filter(status="occupied").count()
    occupancy_rate = round((occupied_units / total_units * 100), 1) if total_units > 0 else 0

    # Open work orders
    open_wo = WorkOrder.objects.exclude(status__in=["completed", "closed"]).count()
    emergency_wo = (
        WorkOrder.objects.filter(priority="emergency")
        .exclude(status__in=["completed", "closed"])
        .count()
    )

    # Get app tiles with badges
    app_tiles = get_app_tiles()

    # Calculate badges for each tile
    for tile in app_tiles:
        tile.badge_count = tile.get_badge_count(request)

    # Organize by category
    tiles_by_category = {}
    for tile in app_tiles:
        if tile.category not in tiles_by_category:
            tiles_by_category[tile.category] = []
        tiles_by_category[tile.category].append(tile)

    # Sort categories by order
    sorted_categories = sorted(
        tiles_by_category.items(), key=lambda x: CATEGORY_INFO[x[0]]["order"]
    )

    return render(
        request,
        "admin_portal/dashboard_launcher.html",
        {
            # Mini KPIs
            "month_revenue": month_revenue,
            "outstanding_balance": outstanding_balance,
            "occupancy_rate": occupancy_rate,
            "occupied_units": occupied_units,
            "total_units": total_units,
            "open_wo": open_wo,
            "emergency_wo": emergency_wo,
            # App launcher data
            "app_tiles": app_tiles,
            "tiles_by_category": sorted_categories,
            "category_info": CATEGORY_INFO,
        },
    )


@admin_required
def admin_analytics_dashboard(request):
    """
    Comprehensive SPLUNK-style analytics dashboard with time-framed metrics,
    trend analysis, charts, and actionable alerts.
    """
    import json
    from datetime import date, timedelta

    from django.db.models import Sum
    from django.urls import reverse

    from apps.billing.models import Invoice, Payment
    from apps.core.dashboard_utils import (
        get_aging_receivables,
        get_lease_metrics,
        get_payment_methods_chart_data,
        get_period_comparison,
        get_revenue_chart_data,
        get_tenant_health_metrics,
        get_workorder_charts_data,
        get_workorder_metrics,
    )
    from apps.leases.models import Lease
    from apps.properties.models import Property, Unit
    from apps.weather.models import WeatherAlert
    from apps.workorders.models import WorkOrder

    # Time range handling
    range_param = request.GET.get("range", "30")
    property_filter = request.GET.get("property", "all")

    today = timezone.now().date()

    if range_param == "7":
        start_date = today - timedelta(days=7)
        range_label = "Last 7 Days"
    elif range_param == "30":
        start_date = today - timedelta(days=30)
        range_label = "Last 30 Days"
    elif range_param == "90":
        start_date = today - timedelta(days=90)
        range_label = "Last 90 Days"
    elif range_param == "ytd":
        start_date = date(today.year, 1, 1)
        range_label = "Year to Date"
    else:
        start_date = today - timedelta(days=30)
        range_label = "Last 30 Days"
        range_param = "30"

    end_date = today

    # Property filter
    property_ids = None
    if property_filter != "all":
        try:
            property_ids = [int(property_filter)]
        except ValueError:
            pass

    # Gather all metrics
    financial = get_period_comparison(start_date, end_date, property_ids)
    workorders = get_workorder_metrics(start_date, end_date, property_ids)
    leases = get_lease_metrics(property_ids)
    tenant_health = get_tenant_health_metrics(start_date, end_date, property_ids)
    aging = get_aging_receivables(property_ids)

    # Chart data
    revenue_chart = get_revenue_chart_data(start_date, end_date, property_ids)
    wo_charts = get_workorder_charts_data(start_date, end_date, property_ids)
    payment_methods_chart = get_payment_methods_chart_data(
        tenant_health["method_breakdown"]
    )

    # Occupancy metrics
    unit_filters = {}
    if property_ids:
        unit_filters["property_id__in"] = property_ids

    total_units = Unit.objects.filter(**unit_filters).count() if unit_filters else Unit.objects.count()
    occupied_units = Unit.objects.filter(status="occupied", **unit_filters).count() if unit_filters else Unit.objects.filter(status="occupied").count()
    occupancy_rate = round((occupied_units / total_units * 100), 1) if total_units > 0 else 0

    # Recent activity
    recent_payments = (
        Payment.objects.filter(status="completed")
        .select_related("tenant", "invoice")
        .order_by("-payment_date")[:5]
    )

    recent_workorders = (
        WorkOrder.objects.select_related("unit", "unit__property")
        .order_by("-updated_at")[:5]
    )

    # Build alerts list
    alerts = []

    # Overdue invoices
    overdue_count = financial["current"]["overdue_count"]
    if overdue_count > 0:
        alerts.append({
            "type": "danger",
            "icon": "bi-exclamation-circle",
            "title": f"{overdue_count} Overdue Invoice{'s' if overdue_count != 1 else ''}",
            "url": reverse("billing_admin:invoice_list") + "?status=overdue",
        })

    # Emergency work orders
    if workorders["emergency_open"] > 0:
        alerts.append({
            "type": "danger",
            "icon": "bi-tools",
            "title": f"{workorders['emergency_open']} Emergency Work Order{'s' if workorders['emergency_open'] != 1 else ''}",
            "url": reverse("workorders_admin:workorder_list") + "?priority=emergency",
        })

    # Expiring leases
    if leases["expiring_30"] > 0:
        alerts.append({
            "type": "warning",
            "icon": "bi-file-earmark-text",
            "title": f"{leases['expiring_30']} Lease{'s' if leases['expiring_30'] != 1 else ''} Expiring in 30 Days",
            "url": reverse("leases_admin:lease_list") + "?expiring=30",
        })

    # Pending signatures
    if leases["pending_signatures"] > 0:
        alerts.append({
            "type": "info",
            "icon": "bi-pen",
            "title": f"{leases['pending_signatures']} Pending Signature{'s' if leases['pending_signatures'] != 1 else ''}",
            "url": reverse("leases_admin:lease_list") + "?signature_status=pending",
        })

    # Weather alerts (last 24 hours)
    recent_weather = (
        WeatherAlert.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24),
            severity__in=["warning", "emergency"],
        )
        .select_related("property")
        .order_by("-created_at")[:3]
    )

    for alert in recent_weather:
        alerts.append({
            "type": "warning" if alert.severity == "warning" else "danger",
            "icon": "bi-cloud-lightning",
            "title": f"{alert.title} - {alert.property.name if alert.property else 'All Properties'}",
            "url": reverse("weather_admin:weather_alert_list"),
        })

    # Properties for filter dropdown
    properties = Property.objects.filter(is_active=True).order_by("name")

    # Calculate aging total
    aging_total = sum(bucket["total"] for bucket in aging.values())

    context = {
        # Time range
        "range": range_param,
        "range_label": range_label,
        "start_date": start_date,
        "end_date": end_date,
        # Property filter
        "property_filter": property_filter,
        "properties": properties,
        # KPIs
        "total_revenue": financial["current"]["total_revenue"],
        "revenue_trend": financial["revenue_trend"],
        "collection_rate": financial["current"]["collection_rate"],
        "collection_trend": financial["collection_trend"],
        "occupancy_rate": occupancy_rate,
        "occupied_units": occupied_units,
        "total_units": total_units,
        "outstanding_balance": financial["current"]["outstanding_balance"],
        "overdue_count": overdue_count,
        # Financial
        "expected_revenue": financial["current"]["expected_revenue"],
        "late_fees_collected": financial["current"]["late_fees_collected"],
        # Work Orders
        "wo_total": workorders["total_in_period"],
        "wo_completed": workorders["completed_in_period"],
        "wo_avg_resolution": workorders["avg_resolution_days"],
        "wo_open_by_priority": workorders["open_by_priority"],
        "wo_total_open": workorders["total_open"],
        "wo_emergency_open": workorders["emergency_open"],
        "wo_by_category": workorders["category_counts"],
        # Leases
        "pending_signatures": leases["pending_signatures"],
        "expiring_30": leases["expiring_30"],
        "expiring_60": leases["expiring_60"],
        "expiring_90": leases["expiring_90"],
        "month_to_month": leases["month_to_month"],
        "total_active_leases": leases["total_active"],
        # Tenant Health
        "on_time_rate": tenant_health["on_time_rate"],
        "avg_days_to_payment": tenant_health["avg_days_to_payment"],
        "payment_methods": tenant_health["method_breakdown"],
        "reward_balance_total": tenant_health["reward_total_balance"],
        "avg_streak": tenant_health["avg_payment_streak"],
        # Aging
        "aging_buckets": aging,
        "aging_total": aging_total,
        # Charts (JSON for JavaScript)
        "revenue_chart_data": json.dumps(revenue_chart),
        "wo_priority_chart_data": json.dumps(wo_charts["priority_chart"]),
        "wo_category_chart_data": json.dumps(wo_charts["category_chart"]),
        "payment_methods_chart_data": json.dumps(payment_methods_chart),
        # Activity & Alerts
        "recent_payments": recent_payments,
        "recent_workorders": recent_workorders,
        "alerts": alerts,
    }

    return render(request, "admin_portal/analytics_dashboard.html", context)


# --- Admin: Tenant Management ---


@admin_required
def admin_tenant_list(request):
    """List all tenant accounts with search, status tabs, and filter."""
    tenants = User.objects.filter(role="tenant").order_by("last_name", "first_name")

    # Status filter: active (default), archived, all
    status_filter = request.GET.get("status", "active")
    if status_filter == "active":
        tenants = tenants.filter(is_active=True)
    elif status_filter == "archived":
        tenants = tenants.filter(is_active=False)
    # "all" shows everything

    # Search filter
    search = request.GET.get("search", "").strip()
    if search:
        tenants = tenants.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone_number__icontains=search)
        )

    # Annotate with active lease info
    from apps.leases.models import Lease

    active_lease_map = {}
    active_leases = Lease.objects.filter(
        status="active", tenant__in=tenants
    ).select_related("unit", "unit__property")
    for lease in active_leases:
        active_lease_map[lease.tenant_id] = lease

    tenant_data = []
    for tenant in tenants:
        tenant_data.append({
            "user": tenant,
            "active_lease": active_lease_map.get(tenant.pk),
            "can_delete": can_delete_tenant(tenant),
        })

    # Counts for tabs
    active_count = User.objects.filter(role="tenant", is_active=True).count()
    archived_count = User.objects.filter(role="tenant", is_active=False).count()

    return render(request, "admin_portal/tenant_list.html", {
        "tenant_data": tenant_data,
        "search": search,
        "status_filter": status_filter,
        "total_count": len(tenant_data),
        "active_count": active_count,
        "archived_count": archived_count,
    })


@admin_required
def admin_tenant_detail_modal(request, pk):
    """Return tenant detail content for modal (AJAX)."""
    tenant = get_object_or_404(User, pk=pk, role="tenant")

    # Gather all related data
    from apps.leases.models import Lease

    leases = Lease.objects.filter(tenant=tenant).select_related(
        "unit", "unit__property"
    ).order_by("-start_date")
    active_lease = leases.filter(status__in=["active", "renewed"]).first()

    # Invoices and payments
    invoices = []
    payments = []
    if hasattr(tenant, "invoices"):
        invoices = tenant.invoices.order_by("-created_at")[:10]
    if hasattr(tenant, "payments"):
        payments = tenant.payments.order_by("-created_at")[:10]

    # Work orders
    work_orders = []
    if hasattr(tenant, "reported_work_orders"):
        work_orders = tenant.reported_work_orders.select_related(
            "unit", "unit__property"
        ).order_by("-created_at")[:5]

    # Onboarding sessions
    onboarding_sessions = []
    if hasattr(tenant, "onboarding_sessions"):
        onboarding_sessions = tenant.onboarding_sessions.select_related(
            "unit", "template"
        ).order_by("-created_at")

    # Emergency contacts
    emergency_contacts = []
    if hasattr(tenant, "emergency_contacts"):
        emergency_contacts = tenant.emergency_contacts.all()

    # Vehicles
    vehicles = []
    if hasattr(tenant, "vehicles"):
        vehicles = tenant.vehicles.all()

    context = {
        "tenant": tenant,
        "profile": getattr(tenant, "tenant_profile", None),
        "leases": leases,
        "active_lease": active_lease,
        "invoices": invoices,
        "payments": payments,
        "work_orders": work_orders,
        "onboarding_sessions": onboarding_sessions,
        "emergency_contacts": emergency_contacts,
        "vehicles": vehicles,
        # Deletion eligibility
        "can_delete": can_delete_tenant(tenant),
        "delete_blockers": get_delete_blockers(tenant),
        "delete_summary": get_delete_summary(tenant),
    }
    return render(request, "admin_portal/_tenant_detail_modal.html", context)


@admin_required
@require_POST
def admin_tenant_delete(request, pk):
    """Delete a tenant (only if eligible)."""
    tenant = get_object_or_404(User, pk=pk, role="tenant")

    if not can_delete_tenant(tenant):
        blockers = get_delete_blockers(tenant)
        messages.error(
            request,
            f"Cannot delete tenant: {', '.join(blockers)}. Consider archiving instead."
        )
        return redirect("accounts_admin:admin_tenant_list")

    name = tenant.get_full_name() or tenant.email
    delete_tenant(tenant, deleted_by=request.user)
    messages.success(request, f"Tenant '{name}' deleted successfully.")
    return redirect("accounts_admin:admin_tenant_list")


@admin_required
@require_POST
def admin_tenant_archive(request, pk):
    """Archive a tenant."""
    tenant = get_object_or_404(User, pk=pk, role="tenant")

    if tenant.is_archived:
        messages.info(request, f"Tenant '{tenant.get_full_name()}' is already archived.")
        return redirect("accounts_admin:admin_tenant_list")

    archive_tenant(tenant)
    messages.success(request, f"Tenant '{tenant.get_full_name() or tenant.email}' archived.")
    return redirect("accounts_admin:admin_tenant_list")


@admin_required
@require_POST
def admin_tenant_restore(request, pk):
    """Restore an archived tenant."""
    tenant = get_object_or_404(User, pk=pk, role="tenant")

    if not tenant.is_archived:
        messages.info(request, f"Tenant '{tenant.get_full_name()}' is already active.")
        return redirect("accounts_admin:admin_tenant_list")

    restore_tenant(tenant)
    messages.success(request, f"Tenant '{tenant.get_full_name() or tenant.email}' restored.")
    return redirect("accounts_admin:admin_tenant_list")


@admin_required
def admin_settings(request):
    """Admin settings overview page."""
    from apps.ai.models import AICapability, AIProvider
    from apps.billing.models import ApiToken, PaymentGatewayConfig
    from apps.notifications.models import EmailConfig, SMSConfig

    gateway_count = PaymentGatewayConfig.objects.count()
    active_gateways = PaymentGatewayConfig.objects.filter(is_active=True).count()
    api_token_count = ApiToken.objects.filter(is_active=True).count()
    staff_count = User.objects.filter(role__in=("admin", "staff"), is_active=True).count()
    email_active = EmailConfig.objects.filter(is_active=True).exists()
    sms_active = SMSConfig.objects.filter(is_active=True).exists()
    ai_provider_count = AIProvider.objects.count()
    ai_active_providers = AIProvider.objects.filter(is_active=True).count()
    ai_capabilities_enabled = AICapability.objects.filter(is_enabled=True).count()

    return render(request, "admin_portal/settings.html", {
        "gateway_count": gateway_count,
        "active_gateways": active_gateways,
        "api_token_count": api_token_count,
        "staff_count": staff_count,
        "email_active": email_active,
        "sms_active": sms_active,
        "ai_provider_count": ai_provider_count,
        "ai_active_providers": ai_active_providers,
        "ai_capabilities_enabled": ai_capabilities_enabled,
    })


# --- Shared ---

def user_logout(request):
    role = getattr(request.user, "role", None)
    logout(request)
    messages.info(request, "You have been logged out.")
    if role in ("admin", "staff"):
        return redirect("accounts_admin:admin_login")
    return redirect("accounts_tenant:tenant_login")


# --- Helpers ---

def _send_otp(otp, user):
    """Send OTP via the configured delivery method."""
    message = f"Your PropManager verification code is: {otp.code}. It expires in 10 minutes."
    if otp.delivery_method == "sms" and user.phone_number:
        from apps.core.services.sms import sms_service
        sms_service.send_sms(to=user.phone_number, body=message)
    else:
        from apps.core.services.email import send_email
        send_email(
            subject="Your PropManager Verification Code",
            message=message,
            recipient_list=[user.email],
        )
