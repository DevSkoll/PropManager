import logging
import uuid

from .base import PaymentGateway, PaymentResult, PaymentStatus, RefundResult

logger = logging.getLogger(__name__)


class SquareGateway(PaymentGateway):
    def __init__(self, config):
        super().__init__(config)
        from square.client import Client
        self.client = Client(
            access_token=config.config.get("access_token", ""),
            environment=config.config.get("environment", "sandbox"),
        )
        self.location_id = config.config.get("location_id", "")

    def create_payment(self, amount, currency, metadata) -> PaymentResult:
        try:
            result = self.client.payments.create_payment({
                "source_id": metadata.get("source_id", ""),
                "idempotency_key": str(uuid.uuid4()),
                "amount_money": {
                    "amount": int(amount * 100),
                    "currency": currency.upper(),
                },
                "location_id": self.location_id,
            })
            if result.is_success():
                payment = result.body["payment"]
                return PaymentResult(
                    success=True,
                    transaction_id=payment["id"],
                    status=PaymentStatus.COMPLETED,
                    raw_response=result.body,
                )
            return PaymentResult(
                success=False,
                error_message=str(result.errors),
            )
        except Exception as e:
            logger.exception("Square payment creation failed")
            return PaymentResult(success=False, error_message=str(e))

    def verify_payment(self, transaction_id) -> PaymentStatus:
        try:
            result = self.client.payments.get_payment(transaction_id)
            if result.is_success():
                status = result.body["payment"]["status"]
                status_map = {
                    "COMPLETED": PaymentStatus.COMPLETED,
                    "APPROVED": PaymentStatus.PENDING,
                    "CANCELLED": PaymentStatus.CANCELLED,
                    "FAILED": PaymentStatus.FAILED,
                }
                return status_map.get(status, PaymentStatus.PENDING)
            return PaymentStatus.FAILED
        except Exception:
            logger.exception("Square payment verification failed")
            return PaymentStatus.FAILED

    def refund_payment(self, transaction_id, amount=None) -> RefundResult:
        try:
            refund_body = {
                "idempotency_key": str(uuid.uuid4()),
                "payment_id": transaction_id,
            }
            if amount:
                refund_body["amount_money"] = {
                    "amount": int(amount * 100),
                    "currency": "USD",
                }
            result = self.client.refunds.refund_payment(refund_body)
            if result.is_success():
                return RefundResult(success=True, refund_id=result.body["refund"]["id"])
            return RefundResult(success=False, error_message=str(result.errors))
        except Exception as e:
            logger.exception("Square refund failed")
            return RefundResult(success=False, error_message=str(e))

    def verify_webhook(self, request):
        try:
            import hashlib
            import hmac
            signature_key = self.config.config.get("webhook_signature_key", "")
            if not signature_key:
                raise ValueError("Webhook signature key not configured")
            notification_url = self.config.config.get("webhook_url", "")
            signature = request.META.get("HTTP_X_SQUARE_HMACSHA256_SIGNATURE", "")
            body = request.body.decode("utf-8")
            # Square webhook verification: HMAC-SHA256(notification_url + body)
            string_to_sign = notification_url + body
            expected = hmac.new(
                signature_key.encode("utf-8"),
                string_to_sign.encode("utf-8"),
                hashlib.sha256,
            ).digest()
            import base64
            expected_b64 = base64.b64encode(expected).decode("utf-8")
            if not hmac.compare_digest(expected_b64, signature):
                raise ValueError("Invalid Square webhook signature")
            import json
            payload = json.loads(body)
            event_type = payload.get("type", "")
            data = payload.get("data", {}).get("object", {})
            return {
                "valid": True,
                "event_type": event_type,
                "transaction_id": data.get("payment", {}).get("id", ""),
                "raw_event": payload,
            }
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Webhook verification failed: {e}")

    def test_connection(self):
        try:
            result = self.client.locations.list_locations()
            if result.is_success():
                return True, "Connection successful"
            return False, str(result.errors)
        except Exception as e:
            return False, str(e)

    def get_client_config(self) -> dict:
        return {
            "application_id": self.config.config.get("application_id", ""),
            "location_id": self.location_id,
        }
