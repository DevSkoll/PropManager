import hashlib
import hmac
import logging
from decimal import Decimal

from .base import PaymentGateway, PaymentResult, PaymentStatus, RefundResult

logger = logging.getLogger(__name__)


class AuthorizeNetGateway(PaymentGateway):
    def __init__(self, config):
        super().__init__(config)
        from authorizenet import apicontractsv1, constants

        self.apicontractsv1 = apicontractsv1
        self.constants = constants

        self.api_login_id = config.config.get("api_login_id", "")
        self.transaction_key = config.config.get("transaction_key", "")
        self.signature_key = config.config.get("signature_key", "")
        self.client_key = config.config.get("client_key", "")

        environment = config.config.get("environment", "sandbox")
        if environment == "production":
            self.environment = constants.PRODUCTION
        else:
            self.environment = constants.SANDBOX

    def _get_merchant_auth(self):
        merchant_auth = self.apicontractsv1.merchantAuthenticationType()
        merchant_auth.name = self.api_login_id
        merchant_auth.transactionKey = self.transaction_key
        return merchant_auth

    def create_payment(self, amount, currency, metadata) -> PaymentResult:
        try:
            from authorizenet.apicontrollers import createTransactionController

            opaque_data_values = metadata.get("opaque_data", {})

            opaque_data = self.apicontractsv1.opaqueDataType()
            opaque_data.dataDescriptor = opaque_data_values.get("data_descriptor", "")
            opaque_data.dataValue = opaque_data_values.get("data_value", "")

            payment_type = self.apicontractsv1.paymentType()
            payment_type.opaqueData = opaque_data

            transaction_request = self.apicontractsv1.transactionRequestType()
            transaction_request.transactionType = "authCaptureTransaction"
            transaction_request.amount = Decimal(str(amount))
            transaction_request.currencyCode = currency
            transaction_request.payment = payment_type

            request = self.apicontractsv1.createTransactionRequest()
            request.merchantAuthentication = self._get_merchant_auth()
            request.transactionRequest = transaction_request

            controller = createTransactionController(request)
            controller.setenvironment(self.environment)
            controller.execute()

            response = controller.getresponse()

            if response is not None and response.messages.resultCode == "Ok":
                if hasattr(response, "transactionResponse") and response.transactionResponse is not None:
                    trans_response = response.transactionResponse
                    return PaymentResult(
                        success=True,
                        transaction_id=str(trans_response.transId),
                        status=PaymentStatus.PENDING,
                        raw_response={
                            "auth_code": str(trans_response.authCode) if hasattr(trans_response, "authCode") else None,
                            "response_code": str(trans_response.responseCode) if hasattr(trans_response, "responseCode") else None,
                        },
                    )

            error_message = "Unknown error"
            if response is not None and hasattr(response, "transactionResponse") and response.transactionResponse is not None:
                trans_response = response.transactionResponse
                if hasattr(trans_response, "errors") and trans_response.errors is not None:
                    error_message = str(trans_response.errors.error[0].errorText)
            elif response is not None and response.messages is not None:
                error_message = str(response.messages.message[0]["text"].text)

            logger.error("Authorize.Net payment creation failed: %s", error_message)
            return PaymentResult(success=False, error_message=error_message)

        except Exception as e:
            logger.exception("Authorize.Net payment creation failed")
            return PaymentResult(success=False, error_message=str(e))

    def verify_payment(self, transaction_id) -> PaymentStatus:
        try:
            from authorizenet.apicontrollers import getTransactionDetailsController

            request = self.apicontractsv1.getTransactionDetailsRequest()
            request.merchantAuthentication = self._get_merchant_auth()
            request.transId = transaction_id

            controller = getTransactionDetailsController(request)
            controller.setenvironment(self.environment)
            controller.execute()

            response = controller.getresponse()

            if response is not None and response.messages.resultCode == "Ok":
                status = response.transaction.transactionStatus

                completed_statuses = {"settledSuccessfully", "capturedPendingSettlement"}
                failed_statuses = {"declined", "expired", "voided"}

                if status in completed_statuses:
                    return PaymentStatus.COMPLETED
                elif status in failed_statuses:
                    return PaymentStatus.FAILED
                elif status == "refundSettledSuccessfully":
                    return PaymentStatus.REFUNDED
                else:
                    return PaymentStatus.PENDING

            logger.error("Authorize.Net payment verification failed: unable to retrieve transaction details")
            return PaymentStatus.FAILED

        except Exception:
            logger.exception("Authorize.Net payment verification failed")
            return PaymentStatus.FAILED

    def refund_payment(self, transaction_id, amount=None) -> RefundResult:
        try:
            from authorizenet.apicontrollers import createTransactionController

            transaction_request = self.apicontractsv1.transactionRequestType()
            transaction_request.transactionType = "refundTransaction"
            transaction_request.refTransId = transaction_id

            if amount is not None:
                transaction_request.amount = Decimal(str(amount))

            request = self.apicontractsv1.createTransactionRequest()
            request.merchantAuthentication = self._get_merchant_auth()
            request.transactionRequest = transaction_request

            controller = createTransactionController(request)
            controller.setenvironment(self.environment)
            controller.execute()

            response = controller.getresponse()

            if response is not None and response.messages.resultCode == "Ok":
                if hasattr(response, "transactionResponse") and response.transactionResponse is not None:
                    return RefundResult(
                        success=True,
                        refund_id=str(response.transactionResponse.transId),
                    )

            error_message = "Unknown error"
            if response is not None and hasattr(response, "transactionResponse") and response.transactionResponse is not None:
                trans_response = response.transactionResponse
                if hasattr(trans_response, "errors") and trans_response.errors is not None:
                    error_message = str(trans_response.errors.error[0].errorText)
            elif response is not None and response.messages is not None:
                error_message = str(response.messages.message[0]["text"].text)

            logger.error("Authorize.Net refund failed: %s", error_message)
            return RefundResult(success=False, error_message=error_message)

        except Exception as e:
            logger.exception("Authorize.Net refund failed")
            return RefundResult(success=False, error_message=str(e))

    def get_client_config(self) -> dict:
        return {
            "api_login_id": self.api_login_id,
            "client_key": self.client_key,
        }

    def verify_webhook(self, request) -> dict:
        signature_header = request.META.get("HTTP_X_ANET_SIGNATURE", "")
        if not signature_header:
            raise ValueError("Missing X-Anet-Signature header")

        # The header value is formatted as "sha512=<hash>"
        if signature_header.startswith("sha512="):
            received_signature = signature_header[7:]
        else:
            received_signature = signature_header

        body = request.body
        if isinstance(body, str):
            body = body.encode("utf-8")

        computed_hash = hmac.new(
            self.signature_key.encode("utf-8"),
            body,
            hashlib.sha512,
        ).hexdigest()

        if not hmac.compare_digest(computed_hash.upper(), received_signature.upper()):
            raise ValueError("Invalid webhook signature")

        import json

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            raise ValueError("Invalid webhook payload")

        event_type = payload.get("eventType", "")
        transaction_id = None
        if "payload" in payload and "id" in payload["payload"]:
            transaction_id = str(payload["payload"]["id"])

        return {
            "valid": True,
            "event_type": event_type,
            "transaction_id": transaction_id,
            "raw_event": payload,
        }

    def test_connection(self) -> tuple:
        try:
            from authorizenet.apicontrollers import authenticateTestController

            request = self.apicontractsv1.authenticateTestRequest()
            request.merchantAuthentication = self._get_merchant_auth()

            controller = authenticateTestController(request)
            controller.setenvironment(self.environment)
            controller.execute()

            response = controller.getresponse()

            if response is not None and response.messages.resultCode == "Ok":
                return True, "Connection successful"

            error_message = "Authentication failed"
            if response is not None and response.messages is not None:
                error_message = str(response.messages.message[0]["text"].text)
            return False, error_message

        except Exception as e:
            logger.exception("Authorize.Net connection test failed")
            return False, str(e)
