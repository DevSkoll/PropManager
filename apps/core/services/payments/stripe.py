import logging

from .base import PaymentGateway, PaymentResult, PaymentStatus, RefundResult

logger = logging.getLogger(__name__)


class StripeGateway(PaymentGateway):
    def __init__(self, config):
        super().__init__(config)
        import stripe
        self.stripe = stripe
        self.stripe.api_key = config.config.get("secret_key", "")

    def create_payment(self, amount, currency, metadata) -> PaymentResult:
        try:
            intent = self.stripe.PaymentIntent.create(
                amount=int(amount * 100),
                currency=currency,
                metadata=metadata,
            )
            return PaymentResult(
                success=True,
                transaction_id=intent.id,
                status=PaymentStatus.PENDING,
                raw_response={"client_secret": intent.client_secret},
            )
        except Exception as e:
            logger.exception("Stripe payment creation failed")
            return PaymentResult(success=False, error_message=str(e))

    def verify_payment(self, transaction_id) -> PaymentStatus:
        try:
            intent = self.stripe.PaymentIntent.retrieve(transaction_id)
            status_map = {
                "succeeded": PaymentStatus.COMPLETED,
                "processing": PaymentStatus.PENDING,
                "canceled": PaymentStatus.CANCELLED,
            }
            return status_map.get(intent.status, PaymentStatus.PENDING)
        except Exception:
            logger.exception("Stripe payment verification failed")
            return PaymentStatus.FAILED

    def refund_payment(self, transaction_id, amount=None) -> RefundResult:
        try:
            params = {"payment_intent": transaction_id}
            if amount:
                params["amount"] = int(amount * 100)
            refund = self.stripe.Refund.create(**params)
            return RefundResult(success=True, refund_id=refund.id)
        except Exception as e:
            logger.exception("Stripe refund failed")
            return RefundResult(success=False, error_message=str(e))

    def get_client_config(self) -> dict:
        return {"publishable_key": self.config.config.get("publishable_key", "")}
