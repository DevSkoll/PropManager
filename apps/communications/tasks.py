import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def send_notification(notification_id):
    """
    Send a notification via its configured channel (email or SMS).
    Called asynchronously via Django-Q2.
    """
    from .models import Notification

    try:
        notification = Notification.objects.select_related("recipient").get(pk=notification_id)
    except Notification.DoesNotExist:
        logger.error("Notification %s does not exist.", notification_id)
        return

    if notification.channel == "email":
        _send_email_notification(notification)
    elif notification.channel == "sms":
        _send_sms_notification(notification)
    elif notification.channel == "in_app":
        # In-app notifications are already persisted; nothing else to dispatch.
        logger.info("In-app notification %s — no external dispatch needed.", notification_id)
    else:
        logger.warning("Unknown channel '%s' for notification %s.", notification.channel, notification_id)


def create_notification(recipient_id, title, body, category="system", channel="in_app", action_url=""):
    """
    Create a Notification record and optionally dispatch it via Django-Q2
    if the channel requires external delivery (email / sms).
    """
    from apps.accounts.models import User

    from .models import Notification

    try:
        recipient = User.objects.get(pk=recipient_id)
    except User.DoesNotExist:
        logger.error("Cannot create notification — user %s does not exist.", recipient_id)
        return None

    notification = Notification.objects.create(
        recipient=recipient,
        title=title,
        body=body,
        category=category,
        channel=channel,
        action_url=action_url,
    )

    if channel in ("email", "sms"):
        try:
            from django_q.tasks import async_task

            async_task(
                "apps.communications.tasks.send_notification",
                str(notification.pk),
                task_name=f"notify-{notification.pk}",
            )
        except Exception:
            # Fallback: dispatch synchronously if Q cluster is not running
            logger.warning("Django-Q2 unavailable — dispatching notification %s synchronously.", notification.pk)
            send_notification(str(notification.pk))

    return notification


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _send_email_notification(notification):
    """Send an email notification to the recipient."""
    from django.core.mail import send_mail

    recipient = notification.recipient
    if not recipient.email:
        logger.warning("User %s has no email address; skipping email notification %s.", recipient, notification.pk)
        return

    try:
        send_mail(
            subject=notification.title,
            message=notification.body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            fail_silently=False,
        )
        logger.info("Email notification %s sent to %s.", notification.pk, recipient.email)
    except Exception:
        logger.exception("Failed to send email notification %s to %s.", notification.pk, recipient.email)


def _send_sms_notification(notification):
    """
    Send an SMS notification to the recipient.
    Placeholder — integrate with Twilio or another provider.
    """
    recipient = notification.recipient
    if not recipient.phone_number:
        logger.warning("User %s has no phone number; skipping SMS notification %s.", recipient, notification.pk)
        return

    # TODO: Integrate with SMS provider (e.g. Twilio)
    logger.info(
        "SMS notification %s would be sent to %s: %s",
        notification.pk,
        recipient.phone_number,
        notification.title,
    )
