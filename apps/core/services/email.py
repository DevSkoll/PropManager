import logging

from django.conf import settings
from django.core.mail import get_connection, send_mail

logger = logging.getLogger(__name__)


def _get_email_connection():
    """
    Return a Django email connection using DB config if available,
    otherwise return (None, None) so Django uses settings.py defaults.
    """
    try:
        from apps.notifications.models import EmailConfig

        config = EmailConfig.objects.filter(is_active=True).first()
        if config:
            connection = get_connection(
                backend=config.email_backend,
                host=config.email_host,
                port=config.email_port,
                username=config.email_host_user,
                password=config.email_host_password,
                use_tls=config.email_use_tls,
                use_ssl=config.email_use_ssl,
            )
            return connection, config.default_from_email
    except Exception:
        logger.exception("Failed to load email config from DB; using settings.py")
    return None, None


def _log_dispatch(channel, status, recipient, subject="", body="", error="", source=""):
    """Create a NotificationLog entry."""
    try:
        from apps.notifications.models import NotificationLog

        NotificationLog.objects.create(
            channel=channel,
            status=status,
            recipient=recipient,
            subject=subject[:500],
            body_preview=body[:500],
            error_message=error,
            source=source,
        )
    except Exception:
        logger.exception("Failed to create notification log entry")


def send_email(subject, message, recipient_list, html_message=None, from_email=None, source=""):
    connection, db_from_email = _get_email_connection()
    from_email = from_email or db_from_email or settings.DEFAULT_FROM_EMAIL

    kwargs = dict(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=recipient_list,
        html_message=html_message,
        fail_silently=False,
    )
    if connection:
        kwargs["connection"] = connection

    try:
        send_mail(**kwargs)
        logger.info("Email sent: subject='%s', to=%s", subject, recipient_list)
        for r in recipient_list:
            _log_dispatch("email", "sent", r, subject=subject, body=message, source=source)
        return True
    except Exception as e:
        logger.exception("Failed to send email to %s", recipient_list)
        for r in recipient_list:
            _log_dispatch(
                "email", "failed", r, subject=subject, body=message, error=str(e), source=source
            )
        return False
