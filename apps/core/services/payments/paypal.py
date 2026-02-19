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

    def verify_webhook(self, request):
        try:
            import json
            webhook_id = self.config.config.get("webhook_id", "")
            if not webhook_id:
                raise ValueError("Webhook ID not configured")
            body = json.loads(request.body)
            # PayPal webhook verification using the SDK
            headers = {
                "auth_algo": request.META.get("HTTP_PAYPAL_AUTH_ALGO", ""),
                "cert_url": request.META.get("HTTP_PAYPAL_CERT_URL", ""),
                "transmission_id": request.META.get("HTTP_PAYPAL_TRANSMISSION_ID", ""),
                "transmission_sig": request.META.get("HTTP_PAYPAL_TRANSMISSION_SIG", ""),
                "transmission_time": request.META.get("HTTP_PAYPAL_TRANSMISSION_TIME", ""),
            }
            verification = self.paypal.WebhookEvent.verify(
                transmission_id=headers["transmission_id"],
                timestamp=headers["transmission_time"],
                webhook_id=webhook_id,
                event_body=json.dumps(body),
                cert_url=headers["cert_url"],
                actual_sig=headers["transmission_sig"],
                auth_algo=headers["auth_algo"],
            )
            if not verification:
                raise ValueError("PayPal webhook verification failed")
            event_type = body.get("event_type", "")
            resource = body.get("resource", {})
            return {
                "valid": True,
                "event_type": event_type,
                "transaction_id": resource.get("id", ""),
                "raw_event": body,
            }
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Webhook verification failed: {e}")

    def test_connection(self):
        try:
            result = self.paypal.Payment.all({"count": 1})
            return True, "Connection successful"
        except Exception as e:
            return False, str(e)

    def get_client_config(self) -> dict:
        return {"client_id": self.config.config.get("client_id", "")}
