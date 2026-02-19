from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.billing.models import Invoice
from apps.core.decorators import admin_required, tenant_required

from .forms import (
    EventTypeSubscriptionForm,
    GroupContactForm,
    NotificationGroupForm,
    SendReminderForm,
    TenantNotificationPreferenceForm,
)
from .models import EventTypeSubscription, GroupContact, NotificationGroup
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
