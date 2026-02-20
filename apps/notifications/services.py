import logging

import requests

from apps.communications.tasks import create_notification
from apps.core.services.email import send_email
from apps.core.services.sms import sms_service

from .models import (
    CATEGORY_CHOICES,
    EventTypeSubscription,
    ReminderLog,
    TenantNotificationPreference,
)

logger = logging.getLogger(__name__)

# Maps event types to tenant notification categories
EVENT_TO_CATEGORY = {
    "new_work_order": None,
    "payment_received": None,
    "new_message": "messages",
    "new_document": None,
    "lease_expiring": None,
    "invoice_overdue": "past_due_balance",
    "weather_alert": "weather_updates",
    "new_tenant": None,
    "reward_earned": "rewards",
    # eDocument signing events
    "edoc_signing_request": None,
    "edoc_signed": None,
    "edoc_completed": None,
}


def _send_webhook(url, payload):
    """POST JSON payload to a webhook URL."""
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Webhook delivered to %s (status %s)", url, resp.status_code)
        return True
    except Exception:
        logger.exception("Webhook delivery failed for %s", url)
        return False


def _notify_contact(contact, subject, body, context=None):
    """Send a notification to a single GroupContact via their configured channel."""
    if contact.channel == "webhook" and contact.webhook_url:
        payload = {
            "event": subject,
            "message": body,
            "service_name": contact.service_name,
            "source": "propmanager",
        }
        if context:
            payload.update(context)
        _send_webhook(contact.webhook_url, payload)
        return

    email = contact.resolved_email()
    phone = contact.resolved_phone()

    if contact.channel in ("email", "both") and email:
        send_email(
            subject=subject,
            message=body,
            recipient_list=[email],
        )

    if contact.channel in ("sms", "both") and phone:
        sms_service.send_sms(to=phone, body=f"{subject}: {body}")


def dispatch_event(event_type, context):
    """
    Central routing function for notification events.

    Phase 1: Send to admin notification groups subscribed to this event type.
    Phase 2: If a tenant_id is in context, check their preferences and send accordingly.
    """
    subject = context.get("subject", "PropManager Notification")
    body = context.get("body", "")

    # Phase 1 — Admin groups
    subscriptions = (
        EventTypeSubscription.objects.filter(
            event_type=event_type, group__is_active=True
        )
        .select_related("group")
        .prefetch_related("group__contacts", "group__contacts__user")
    )

    for sub in subscriptions:
        for contact in sub.group.contacts.filter(is_active=True):
            try:
                _notify_contact(contact, subject, body, context=context)
            except Exception:
                logger.exception(
                    "Failed to notify contact %s in group %s for event %s",
                    contact.pk,
                    sub.group.name,
                    event_type,
                )

    # Phase 2 — Tenant preferences
    tenant_id = context.get("tenant_id")
    if tenant_id:
        category = EVENT_TO_CATEGORY.get(event_type)
        channel = "email"  # default

        if category:
            try:
                pref = TenantNotificationPreference.objects.get(
                    tenant_id=tenant_id, category=category
                )
                channel = pref.channel
            except TenantNotificationPreference.DoesNotExist:
                pass

        # Always create an in-app notification
        action_url = context.get("action_url", "")
        notification_category = context.get("notification_category", "system")
        create_notification(
            recipient_id=str(tenant_id),
            title=subject,
            body=body,
            category=notification_category,
            channel="in_app",
            action_url=action_url,
        )

        # Also send via external channel per preference
        if channel in ("email", "both"):
            from apps.accounts.models import User

            try:
                tenant = User.objects.get(pk=tenant_id)
                if tenant.email:
                    send_email(
                        subject=subject,
                        message=body,
                        recipient_list=[tenant.email],
                    )
            except User.DoesNotExist:
                logger.error("Tenant %s does not exist.", tenant_id)

        if channel in ("sms", "both"):
            from apps.accounts.models import User

            try:
                tenant = User.objects.get(pk=tenant_id)
                if tenant.phone_number:
                    sms_service.send_sms(
                        to=tenant.phone_number, body=f"{subject}: {body}"
                    )
            except User.DoesNotExist:
                logger.error("Tenant %s does not exist.", tenant_id)


def send_invoice_reminder(invoice, sent_by):
    """
    Send a payment reminder for a specific invoice and create an audit log entry.

    Returns the ReminderLog instance.
    """
    tenant = invoice.tenant
    balance = invoice.balance_due
    due_date = invoice.due_date.strftime("%B %d, %Y") if invoice.due_date else "N/A"

    message = (
        f"Payment Reminder: Invoice {invoice.invoice_number} has an outstanding "
        f"balance of ${balance:.2f}, due {due_date}. "
        f"Please submit your payment at your earliest convenience."
    )

    # Determine channel from tenant preferred_contact
    channel = getattr(tenant, "preferred_contact", "email") or "email"

    if channel == "email" and tenant.email:
        send_email(
            subject=f"Payment Reminder — Invoice {invoice.invoice_number}",
            message=message,
            recipient_list=[tenant.email],
        )
    elif channel == "sms" and tenant.phone_number:
        sms_service.send_sms(to=tenant.phone_number, body=message)
    else:
        # Fallback to email if SMS not available
        if tenant.email:
            channel = "email"
            send_email(
                subject=f"Payment Reminder — Invoice {invoice.invoice_number}",
                message=message,
                recipient_list=[tenant.email],
            )

    # Create in-app notification
    create_notification(
        recipient_id=str(tenant.pk),
        title=f"Payment Reminder — Invoice {invoice.invoice_number}",
        body=message,
        category="billing",
        channel="in_app",
        action_url=f"/tenant/billing/invoices/{invoice.pk}/",
    )

    # Create audit log
    log = ReminderLog.objects.create(
        invoice=invoice,
        sent_by=sent_by,
        channel=channel,
        message=message,
    )

    return log
