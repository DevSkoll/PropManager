import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_email(subject, message, recipient_list, html_message=None, from_email=None):
    from_email = from_email or settings.DEFAULT_FROM_EMAIL
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Email sent: subject='{subject}', to={recipient_list}")
        return True
    except Exception:
        logger.exception(f"Failed to send email to {recipient_list}")
        return False
