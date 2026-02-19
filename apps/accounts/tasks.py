import logging

logger = logging.getLogger(__name__)


def send_otp_email(user_email, otp_code):
    """Django-Q2 task: Send OTP code via email."""
    from apps.core.services.email import send_email

    send_email(
        subject="Your PropManager Verification Code",
        message=f"Your verification code is: {otp_code}. It expires in 10 minutes.",
        recipient_list=[user_email],
    )
    logger.info(f"OTP email sent to {user_email}")


def send_otp_sms(phone_number, otp_code):
    """Django-Q2 task: Send OTP code via SMS."""
    from apps.core.services.sms import sms_service

    sms_service.send_sms(
        to=phone_number,
        body=f"Your PropManager verification code is: {otp_code}. It expires in 10 minutes.",
    )
    logger.info(f"OTP SMS sent to {phone_number}")
