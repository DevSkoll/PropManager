import logging

from .base import PaymentGateway, PaymentResult, PaymentStatus, RefundResult

logger = logging.getLogger(__name__)


class BraintreeGateway(PaymentGateway):
    def __init__(self, config):
        super().__init__(config)
        import braintree

        self.braintree = braintree

        environment = config.config.get("environment", "sandbox")
        if environment == "production":
            bt_environment = braintree.Environment.Production
        else:
            bt_environment = braintree.Environment.Sandbox

        self.gateway = braintree.BraintreeGateway(
            braintree.Configuration(
                environment=bt_environment,
                merchant_id=config.config.get("merchant_id", ""),
                public_key=config.config.get("public_key", ""),
                private_key=config.config.get("private_key", ""),
            )
        )

    def create_payment(self, amount, currency, metadata) -> PaymentResult:
        try:
            result = self.gateway.transaction.sale({
                "amount": str(amount),
                "payment_method_nonce": metadata["nonce"],
                "options": {
                    "submit_for_settlement": True,
                },
            })

            if result.is_success:
                return PaymentResult(
                    success=True,
                    transaction_id=result.transaction.id,
                    status=PaymentStatus.PENDING,
                    raw_response={
                        "status": result.transaction.status,
                        "processor_response_code": result.transaction.processor_response_code,
                        "processor_response_text": result.transaction.processor_response_text,
                    },
                )

            error_message = "Transaction failed"
            if result.message:
                error_message = result.message

            logger.error("Braintree payment creation failed: %s", error_message)
            return PaymentResult(success=False, error_message=error_message)

        except Exception as e:
            logger.exception("Braintree payment creation failed")
            return PaymentResult(success=False, error_message=str(e))

    def verify_payment(self, transaction_id) -> PaymentStatus:
        try:
            transaction = self.gateway.transaction.find(transaction_id)

            completed_statuses = {
                self.braintree.Transaction.Status.Settled,
                self.braintree.Transaction.Status.Settling,
                self.braintree.Transaction.Status.SubmittedForSettlement,
            }
            failed_statuses = {
                self.braintree.Transaction.Status.GatewayRejected,
                self.braintree.Transaction.Status.ProcessorDeclined,
            }

            if transaction.status in completed_statuses:
                return PaymentStatus.COMPLETED
            elif transaction.status in failed_statuses:
                return PaymentStatus.FAILED
            elif transaction.status == self.braintree.Transaction.Status.Voided:
                return PaymentStatus.CANCELLED
            else:
                return PaymentStatus.PENDING

        except Exception:
            logger.exception("Braintree payment verification failed")
            return PaymentStatus.FAILED

    def refund_payment(self, transaction_id, amount=None) -> RefundResult:
        try:
            if amount is not None:
                result = self.gateway.transaction.refund(transaction_id, str(amount))
            else:
                result = self.gateway.transaction.refund(transaction_id)

            if result.is_success:
                return RefundResult(
                    success=True,
                    refund_id=result.transaction.id,
                )

            error_message = "Refund failed"
            if result.message:
                error_message = result.message

            logger.error("Braintree refund failed: %s", error_message)
            return RefundResult(success=False, error_message=error_message)

        except Exception as e:
            logger.exception("Braintree refund failed")
            return RefundResult(success=False, error_message=str(e))

    def get_client_config(self) -> dict:
        try:
            client_token = self.gateway.client_token.generate()
            return {"client_token": client_token}
        except Exception as e:
            logger.exception("Braintree client token generation failed")
            return {"error": str(e)}

    def verify_webhook(self, request) -> dict:
        bt_signature = request.POST.get("bt_signature", "")
        bt_payload = request.POST.get("bt_payload", "")

        if not bt_signature or not bt_payload:
            raise ValueError("Missing bt_signature or bt_payload in request")

        try:
            notification = self.gateway.webhook_notification.parse(
                bt_signature,
                bt_payload,
            )
        except Exception:
            logger.exception("Braintree webhook verification failed")
            raise ValueError("Invalid webhook signature")

        transaction_id = None
        if notification.subject and hasattr(notification.subject, "transaction"):
            transaction_id = notification.subject.transaction.id if notification.subject.transaction else None

        return {
            "valid": True,
            "event_type": notification.kind,
            "transaction_id": transaction_id,
            "raw_event": {
                "kind": notification.kind,
                "timestamp": str(notification.timestamp),
            },
        }

    def test_connection(self) -> tuple:
        try:
            self.gateway.client_token.generate()
            return True, "Connection successful"
        except Exception as e:
            logger.exception("Braintree connection test failed")
            return False, str(e)
