import logging

from .base import PaymentGateway, PaymentResult, PaymentStatus, RefundResult

logger = logging.getLogger(__name__)


class PayPalGateway(PaymentGateway):
    def __init__(self, config):
        super().__init__(config)
        import paypalrestsdk
        paypalrestsdk.configure({
            "mode": config.config.get("mode", "sandbox"),
            "client_id": config.config.get("client_id", ""),
            "client_secret": config.config.get("client_secret", ""),
        })
        self.paypal = paypalrestsdk

    def create_payment(self, amount, currency, metadata) -> PaymentResult:
        try:
            payment = self.paypal.Payment({
                "intent": "sale",
                "payer": {"payment_method": "paypal"},
                "transactions": [{
                    "amount": {"total": f"{amount:.2f}", "currency": currency.upper()},
                    "description": metadata.get("description", "Payment"),
                }],
                "redirect_urls": {
                    "return_url": metadata.get("return_url", ""),
                    "cancel_url": metadata.get("cancel_url", ""),
                },
            })
            if payment.create():
                approval_url = next(
                    (link.href for link in payment.links if link.rel == "approval_url"), None
                )
                return PaymentResult(
                    success=True,
                    transaction_id=payment.id,
                    status=PaymentStatus.PENDING,
                    raw_response={"approval_url": approval_url},
                )
            return PaymentResult(success=False, error_message=str(payment.error))
        except Exception as e:
            logger.exception("PayPal payment creation failed")
            return PaymentResult(success=False, error_message=str(e))

    def verify_payment(self, transaction_id) -> PaymentStatus:
        try:
            payment = self.paypal.Payment.find(transaction_id)
            if payment.state == "approved":
                return PaymentStatus.COMPLETED
            return PaymentStatus.PENDING
        except Exception:
            logger.exception("PayPal payment verification failed")
            return PaymentStatus.FAILED

    def refund_payment(self, transaction_id, amount=None) -> RefundResult:
        try:
            payment = self.paypal.Payment.find(transaction_id)
            sale = payment.transactions[0].related_resources[0].sale
            refund_data = {}
            if amount:
                refund_data = {"amount": {"total": f"{amount:.2f}", "currency": "USD"}}
            refund = sale.refund(refund_data)
            if refund.success():
                return RefundResult(success=True, refund_id=refund.id)
            return RefundResult(success=False, error_message="Refund failed")
        except Exception as e:
            logger.exception("PayPal refund failed")
            return RefundResult(success=False, error_message=str(e))

    def get_client_config(self) -> dict:
        return {"client_id": self.config.config.get("client_id", "")}
