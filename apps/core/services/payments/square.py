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

    def get_client_config(self) -> dict:
        return {
            "application_id": self.config.config.get("application_id", ""),
            "location_id": self.location_id,
        }
