import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class TwilioService:
    """Twilio service adapter. Reads config from DB first, then settings.py."""

    def __init__(self):
        self._client = None
        self._account_sid = None
        self._auth_token = None
        self._phone_number = None

    def _load_config(self):
        """Load config from active SMSConfig in DB, or fall back to settings."""
        try:
            from apps.notifications.models import SMSConfig

            config = SMSConfig.objects.filter(is_active=True).first()
            if config:
                self._account_sid = config.account_sid
                self._auth_token = config.auth_token
                self._phone_number = config.phone_number
                self._client = None  # Force re-creation with new creds
                return
        except Exception:
            logger.exception("Failed to load SMS config from DB; using settings.py")

        self._account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", "")
        self._auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
        self._phone_number = getattr(settings, "TWILIO_PHONE_NUMBER", "")
        self._client = None

    def refresh(self):
        """Force reload of credentials from DB/settings on next access."""
        self._account_sid = None
        self._auth_token = None
        self._phone_number = None
        self._client = None

    @property
    def account_sid(self):
        if self._account_sid is None:
            self._load_config()
        return self._account_sid

    @property
    def auth_token(self):
        if self._auth_token is None:
            self._load_config()
        return self._auth_token

    @property
    def phone_number(self):
        if self._phone_number is None:
            self._load_config()
        return self._phone_number

    @property
    def client(self):
        if self._client is None:
            if not self.account_sid or not self.auth_token:
                logger.warning("Twilio credentials not configured")
                return None
            from twilio.rest import Client

            self._client = Client(self.account_sid, self.auth_token)
        return self._client

    def send_sms(self, to, body, source=""):
        # Refresh config on each send to pick up DB changes immediately
        self.refresh()

        if not self.client:
            logger.info("SMS (not sent - no client): to=%s, body=%s", to, body)
            self._log_dispatch("failed", to, body=body, error="No Twilio client configured", source=source)
            return None
        try:
            message = self.client.messages.create(
                body=body,
                from_=self.phone_number,
                to=to,
            )
            logger.info("SMS sent: sid=%s, to=%s", message.sid, to)
            self._log_dispatch("sent", to, body=body, source=source)
            return message.sid
        except Exception as e:
            logger.exception("Failed to send SMS to %s", to)
            self._log_dispatch("failed", to, body=body, error=str(e), source=source)
            return None

    def _log_dispatch(self, status, recipient, body="", error="", source=""):
        try:
            from apps.notifications.models import NotificationLog

            NotificationLog.objects.create(
                channel="sms",
                status=status,
                recipient=recipient,
                body_preview=body[:500],
                error_message=error,
                source=source,
            )
        except Exception:
            logger.exception("Failed to create SMS notification log entry")


sms_service = TwilioService()
