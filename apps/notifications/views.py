from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.billing.models import Invoice
from apps.core.decorators import admin_required, tenant_required

from .forms import (
    EmailConfigForm,
    EventTypeSubscriptionForm,
    GroupContactForm,
    NotificationGroupForm,
    SMSConfigForm,
    SendReminderForm,
    TenantNotificationPreferenceForm,
)
from .models import (
    EmailConfig,
    EventTypeSubscription,
    GroupContact,
    NotificationGroup,
    NotificationLog,
    SMSConfig,
)
from .services import send_invoice_reminder


# ===========================================================================
# Admin Views — Notification Groups
# ===========================================================================


@admin_required
def admin_group_list(request):
    groups = NotificationGroup.objects.prefetch_related("contacts", "subscriptions").all()
    return render(request, "notifications/admin_group_list.html", {"groups": groups})


@admin_required
def admin_group_create(request):
    if request.method == "POST":
        form = NotificationGroupForm(request.POST)
        event_form = EventTypeSubscriptionForm(request.POST)
        if form.is_valid() and event_form.is_valid():
            group = form.save(commit=False)
            group.created_by = request.user
            group.save()
            # Create event subscriptions
            for event_type in event_form.cleaned_data["event_types"]:
                EventTypeSubscription.objects.create(
                    group=group, event_type=event_type
                )
            messages.success(request, f'Notification group "{group.name}" created.')
            return redirect("notifications_admin:group_detail", pk=group.pk)
    else:
        form = NotificationGroupForm()
        event_form = EventTypeSubscriptionForm()

    return render(
        request,
        "notifications/admin_group_form.html",
        {"form": form, "event_form": event_form, "editing": False},
    )


@admin_required
def admin_group_detail(request, pk):
    group = get_object_or_404(
        NotificationGroup.objects.prefetch_related(
            "contacts", "contacts__user", "subscriptions"
        ),
        pk=pk,
    )
    return render(
        request, "notifications/admin_group_detail.html", {"group": group}
    )


@admin_required
def admin_group_edit(request, pk):
    group = get_object_or_404(NotificationGroup, pk=pk)
    current_events = list(
        group.subscriptions.values_list("event_type", flat=True)
    )

    if request.method == "POST":
        form = NotificationGroupForm(request.POST, instance=group)
        event_form = EventTypeSubscriptionForm(request.POST)
        if form.is_valid() and event_form.is_valid():
            group = form.save(commit=False)
            group.updated_by = request.user
            group.save()
            # Sync event subscriptions
            new_events = set(event_form.cleaned_data["event_types"])
            old_events = set(current_events)
            # Remove unselected
            EventTypeSubscription.objects.filter(
                group=group, event_type__in=old_events - new_events
            ).delete()
            # Add newly selected
            for event_type in new_events - old_events:
                EventTypeSubscription.objects.create(
                    group=group, event_type=event_type
                )
            messages.success(request, f'Notification group "{group.name}" updated.')
            return redirect("notifications_admin:group_detail", pk=group.pk)
    else:
        form = NotificationGroupForm(instance=group)
        event_form = EventTypeSubscriptionForm(
            initial={"event_types": current_events}
        )

    return render(
        request,
        "notifications/admin_group_form.html",
        {"form": form, "event_form": event_form, "editing": True, "group": group},
    )


@admin_required
def admin_group_delete(request, pk):
    group = get_object_or_404(NotificationGroup, pk=pk)
    if request.method == "POST":
        name = group.name
        group.delete()
        messages.success(request, f'Notification group "{name}" deleted.')
        return redirect("notifications_admin:group_list")
    return render(
        request,
        "notifications/admin_group_confirm_delete.html",
        {"group": group},
    )


# ===========================================================================
# Admin Views — Group Contacts
# ===========================================================================


@admin_required
def admin_contact_add(request, group_pk):
    group = get_object_or_404(NotificationGroup, pk=group_pk)
    if request.method == "POST":
        form = GroupContactForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.group = group
            contact.save()
            messages.success(request, f"Contact added to {group.name}.")
            return redirect("notifications_admin:group_detail", pk=group.pk)
    else:
        form = GroupContactForm()

    return render(
        request,
        "notifications/admin_contact_form.html",
        {"form": form, "group": group, "editing": False},
    )


@admin_required
def admin_contact_edit(request, pk):
    contact = get_object_or_404(
        GroupContact.objects.select_related("group"), pk=pk
    )
    if request.method == "POST":
        form = GroupContactForm(request.POST, instance=contact)
        if form.is_valid():
            form.save()
            messages.success(request, "Contact updated.")
            return redirect(
                "notifications_admin:group_detail", pk=contact.group.pk
            )
    else:
        form = GroupContactForm(instance=contact)

    return render(
        request,
        "notifications/admin_contact_form.html",
        {"form": form, "group": contact.group, "editing": True, "contact": contact},
    )


@admin_required
def admin_contact_delete(request, pk):
    contact = get_object_or_404(
        GroupContact.objects.select_related("group"), pk=pk
    )
    if request.method == "POST":
        group = contact.group
        contact.delete()
        messages.success(request, "Contact removed.")
        return redirect("notifications_admin:group_detail", pk=group.pk)
    return render(
        request,
        "notifications/admin_contact_confirm_delete.html",
        {"contact": contact},
    )


# ===========================================================================
# Admin Views — Send Reminder
# ===========================================================================


@admin_required
def admin_send_reminder(request, invoice_pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related("tenant", "lease", "lease__unit"),
        pk=invoice_pk,
    )
    tenant = invoice.tenant
    channel = getattr(tenant, "preferred_contact", "email") or "email"

    if request.method == "POST":
        form = SendReminderForm(request.POST)
        if form.is_valid():
            log = send_invoice_reminder(invoice, sent_by=request.user)
            messages.success(
                request,
                f"Payment reminder sent to {tenant.get_full_name() or tenant.username} via {log.channel}.",
            )
            return redirect("billing_admin:invoice_detail", pk=invoice.pk)
    else:
        form = SendReminderForm()

    return render(
        request,
        "notifications/admin_send_reminder.html",
        {
            "form": form,
            "invoice": invoice,
            "tenant": tenant,
            "channel": channel,
        },
    )


# ===========================================================================
# Admin Views — Communications Settings
# ===========================================================================


@admin_required
def admin_communications_settings(request):
    """Communications settings hub: email and SMS config with status."""
    email_config = EmailConfig.objects.filter(is_active=True).first()
    sms_config = SMSConfig.objects.filter(is_active=True).first()
    recent_logs = NotificationLog.objects.all()[:50]

    return render(
        request,
        "notifications/admin_communications_settings.html",
        {
            "email_config": email_config,
            "sms_config": sms_config,
            "recent_logs": recent_logs,
        },
    )


@admin_required
def admin_email_config(request, pk=None):
    """Create or edit an email configuration."""
    if pk:
        instance = get_object_or_404(EmailConfig, pk=pk)
    else:
        instance = None

    if request.method == "POST":
        form = EmailConfigForm(request.POST, instance=instance)
        if form.is_valid():
            config = form.save(commit=False)
            if not instance:
                config.created_by = request.user
            config.updated_by = request.user
            config.save()
            messages.success(request, "Email configuration saved.")
            return redirect("notifications_admin:communications_settings")
    else:
        form = EmailConfigForm(instance=instance)

    return render(
        request,
        "notifications/admin_email_config_form.html",
        {"form": form, "editing": instance is not None},
    )


@admin_required
def admin_sms_config(request, pk=None):
    """Create or edit an SMS configuration."""
    if pk:
        instance = get_object_or_404(SMSConfig, pk=pk)
    else:
        instance = None

    if request.method == "POST":
        form = SMSConfigForm(request.POST, instance=instance)
        if form.is_valid():
            config = form.save(commit=False)
            if not instance:
                config.created_by = request.user
            config.updated_by = request.user
            config.save()
            messages.success(request, "SMS configuration saved.")
            return redirect("notifications_admin:communications_settings")
    else:
        form = SMSConfigForm(instance=instance)

    return render(
        request,
        "notifications/admin_sms_config_form.html",
        {"form": form, "editing": instance is not None},
    )


@admin_required
@require_POST
def admin_email_test(request, pk):
    """Test email config by sending a test email to the current admin."""
    from django.core.mail import get_connection, send_mail
    from django.utils import timezone

    config = get_object_or_404(EmailConfig, pk=pk)
    try:
        connection = get_connection(
            backend=config.email_backend,
            host=config.email_host,
            port=config.email_port,
            username=config.email_host_user,
            password=config.email_host_password,
            use_tls=config.email_use_tls,
            use_ssl=config.email_use_ssl,
        )
        send_mail(
            subject="PropManager Email Test",
            message=(
                f"This is a test email sent at {timezone.now():%Y-%m-%d %H:%M:%S}. "
                f"Your email configuration is working correctly."
            ),
            from_email=config.default_from_email,
            recipient_list=[request.user.email],
            connection=connection,
            fail_silently=False,
        )
        config.last_tested_at = timezone.now()
        config.last_test_success = True
        config.save(update_fields=["last_tested_at", "last_test_success"])
        return JsonResponse(
            {"success": True, "message": f"Test email sent to {request.user.email}"}
        )
    except Exception as e:
        config.last_tested_at = timezone.now()
        config.last_test_success = False
        config.save(update_fields=["last_tested_at", "last_test_success"])
        return JsonResponse({"success": False, "message": str(e)})


@admin_required
@require_POST
def admin_sms_test(request, pk):
    """Test SMS config by verifying Twilio credentials via API."""
    from django.utils import timezone

    config = get_object_or_404(SMSConfig, pk=pk)
    try:
        from twilio.rest import Client

        client = Client(config.account_sid, config.auth_token)
        account = client.api.accounts(config.account_sid).fetch()
        config.last_tested_at = timezone.now()
        config.last_test_success = True
        config.save(update_fields=["last_tested_at", "last_test_success"])
        return JsonResponse(
            {
                "success": True,
                "message": f"Twilio connection verified. Account: {account.friendly_name}",
            }
        )
    except Exception as e:
        config.last_tested_at = timezone.now()
        config.last_test_success = False
        config.save(update_fields=["last_tested_at", "last_test_success"])
        return JsonResponse({"success": False, "message": str(e)})


@admin_required
def admin_notification_log(request):
    """View notification dispatch log with filters."""
    logs = NotificationLog.objects.all()

    channel_filter = request.GET.get("channel", "")
    status_filter = request.GET.get("status", "")

    if channel_filter:
        logs = logs.filter(channel=channel_filter)
    if status_filter:
        logs = logs.filter(status=status_filter)

    return render(
        request,
        "notifications/admin_notification_log.html",
        {
            "logs": logs[:200],
            "channel_filter": channel_filter,
            "status_filter": status_filter,
        },
    )


# ===========================================================================
# Tenant Views
# ===========================================================================


@tenant_required
def tenant_notification_preferences(request):
    if request.method == "POST":
        form = TenantNotificationPreferenceForm(request.POST, tenant=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Notification preferences saved.")
            return redirect("notifications_tenant:preferences")
    else:
        form = TenantNotificationPreferenceForm(tenant=request.user)

    return render(
        request,
        "notifications/tenant_notification_preferences.html",
        {"form": form},
    )
