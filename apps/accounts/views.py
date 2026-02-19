from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.core.decorators import admin_required, tenant_required

from .forms import AdminLoginForm, OTPVerifyForm, TenantLoginForm, TenantProfileForm
from .models import OTPToken

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
            next_url = request.GET.get("next", "accounts_tenant:tenant_dashboard")
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
    from django.db.models import Count, Sum
    from apps.properties.models import Property, Unit
    from apps.billing.models import Invoice
    from apps.workorders.models import WorkOrder
    from apps.leases.models import Lease
    from apps.weather.models import WeatherAlert

    total_properties = Property.objects.filter(is_active=True).count()
    total_units = Unit.objects.count()
    occupied_units = Unit.objects.filter(status="occupied").count()
    occupancy_rate = round((occupied_units / total_units * 100), 1) if total_units > 0 else 0

    active_tenants = User.objects.filter(role="tenant", is_active=True).count()

    open_wo = WorkOrder.objects.exclude(status__in=["completed", "closed"]).count()

    outstanding = Invoice.objects.filter(
        status__in=["issued", "partial", "overdue"]
    ).aggregate(
        total=Sum("total_amount"), paid=Sum("amount_paid")
    )
    outstanding_balance = (outstanding["total"] or 0) - (outstanding["paid"] or 0)

    expiring_leases = Lease.objects.filter(
        status="active",
        end_date__lte=timezone.now().date() + timezone.timedelta(days=60),
        end_date__gte=timezone.now().date(),
    ).select_related("tenant", "unit", "unit__property").count()

    recent_alerts = WeatherAlert.objects.select_related("property").order_by("-created_at")[:5]

    recent_work_orders = WorkOrder.objects.select_related(
        "unit", "unit__property", "reported_by"
    ).order_by("-created_at")[:10]

    return render(request, "admin_portal/dashboard.html", {
        "total_properties": total_properties,
        "active_tenants": active_tenants,
        "open_wo": open_wo,
        "outstanding_balance": outstanding_balance,
        "occupancy_rate": occupancy_rate,
        "total_units": total_units,
        "occupied_units": occupied_units,
        "expiring_leases": expiring_leases,
        "recent_alerts": recent_alerts,
        "recent_work_orders": recent_work_orders,
    })


# --- Admin: Tenant Management ---


@admin_required
def admin_tenant_list(request):
    """List all tenant accounts with search and filter."""
    tenants = User.objects.filter(role="tenant").order_by("last_name", "first_name")

    search = request.GET.get("search", "").strip()
    if search:
        tenants = tenants.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone_number__icontains=search)
        )

    status_filter = request.GET.get("status", "")
    if status_filter == "active":
        tenants = tenants.filter(is_active=True)
    elif status_filter == "inactive":
        tenants = tenants.filter(is_active=False)

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
        })

    return render(request, "admin_portal/tenant_list.html", {
        "tenant_data": tenant_data,
        "search": search,
        "status_filter": status_filter,
        "total_count": len(tenant_data),
    })


@admin_required
def admin_settings(request):
    """Admin settings overview page."""
    from apps.billing.models import ApiToken, PaymentGatewayConfig

    gateway_count = PaymentGatewayConfig.objects.count()
    active_gateways = PaymentGatewayConfig.objects.filter(is_active=True).count()
    api_token_count = ApiToken.objects.filter(is_active=True).count()
    staff_count = User.objects.filter(role__in=("admin", "staff"), is_active=True).count()

    return render(request, "admin_portal/settings.html", {
        "gateway_count": gateway_count,
        "active_gateways": active_gateways,
        "api_token_count": api_token_count,
        "staff_count": staff_count,
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
