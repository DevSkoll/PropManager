import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class TwilioService:
    """Twilio service adapter. Currently supports SMS; designed for future voice/AI expansion."""

    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.phone_number = settings.TWILIO_PHONE_NUMBER
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not self.account_sid or not self.auth_token:
                logger.warning("Twilio credentials not configured")
                return None
            from twilio.rest import Client
            self._client = Client(self.account_sid, self.auth_token)
        return self._client

    def send_sms(self, to, body):
        if not self.client:
            logger.info(f"SMS (not sent - no client): to={to}, body={body}")
            return None
        try:
            message = self.client.messages.create(
                body=body,
                from_=self.phone_number,
                to=to,
            )
            logger.info(f"SMS sent: sid={message.sid}, to={to}")
            return message.sid
        except Exception:
            logger.exception(f"Failed to send SMS to {to}")
            return None


sms_service = TwilioService()
