import logging

from .base import PaymentGateway, PaymentResult, PaymentStatus, RefundResult

logger = logging.getLogger(__name__)


class PlaidAchGateway(PaymentGateway):
    def __init__(self, config):
        super().__init__(config)
        import plaid
        from plaid.api import plaid_api
        from plaid.model.country_code import CountryCode
        from plaid.model.products import Products
        import stripe

        self.stripe = stripe
        self.stripe.api_key = config.config.get("stripe_secret_key", "")
        self.stripe_publishable_key = config.config.get(
            "stripe_publishable_key", ""
        )

        plaid_env = config.config.get("plaid_environment", "sandbox")
        env_map = {
            "sandbox": plaid.Environment.Sandbox,
            "development": plaid.Environment.Development,
            "production": plaid.Environment.Production,
        }
        plaid_config = plaid.Configuration(
            host=env_map.get(plaid_env, plaid.Environment.Sandbox),
            api_key={
                "clientId": config.config.get("plaid_client_id", ""),
                "secret": config.config.get("plaid_secret", ""),
            },
        )
        api_client = plaid.ApiClient(plaid_config)
        self.plaid_client = plaid_api.PlaidApi(api_client)
        self.CountryCode = CountryCode
        self.Products = Products

    def create_payment(self, amount, currency, metadata) -> PaymentResult:
        try:
            from plaid.model.item_public_token_exchange_request import (
                ItemPublicTokenExchangeRequest,
            )
            from plaid.model.processor_stripe_bank_account_token_create_request import (
                ProcessorStripeBankAccountTokenCreateRequest,
            )

            public_token = metadata.get("public_token")
            account_id = metadata.get("account_id")

            if not public_token or not account_id:
                return PaymentResult(
                    success=False,
                    error_message="public_token and account_id are required in metadata",
                )

            # Exchange public token for access token
            exchange_request = ItemPublicTokenExchangeRequest(
                public_token=public_token,
            )
            exchange_response = self.plaid_client.item_public_token_exchange(
                exchange_request
            )
            access_token = exchange_response.access_token

            # Create Stripe bank account token via Plaid processor
            processor_request = ProcessorStripeBankAccountTokenCreateRequest(
                access_token=access_token,
                account_id=account_id,
            )
            processor_response = (
                self.plaid_client.processor_stripe_bank_account_token_create(
                    processor_request
                )
            )
            stripe_bank_token = processor_response.stripe_bank_account_token

            # Create Stripe PaymentIntent for ACH
            intent = self.stripe.PaymentIntent.create(
                amount=int(amount * 100),
                currency=currency or "usd",
                payment_method_types=["us_bank_account"],
                payment_method_data={
                    "type": "us_bank_account",
                    "us_bank_account": {
                        "financial_connections_account": stripe_bank_token,
                    },
                },
                metadata=metadata,
            )

            return PaymentResult(
                success=True,
                transaction_id=intent.id,
                status=PaymentStatus.PENDING,
                raw_response={
                    "client_secret": intent.client_secret,
                    "stripe_bank_token": stripe_bank_token,
                },
            )
        except Exception as e:
            logger.exception("Plaid ACH payment creation failed")
            return PaymentResult(success=False, error_message=str(e))

    def verify_payment(self, transaction_id) -> PaymentStatus:
        try:
            intent = self.stripe.PaymentIntent.retrieve(transaction_id)
            status_map = {
                "succeeded": PaymentStatus.COMPLETED,
                "processing": PaymentStatus.PENDING,
                "canceled": PaymentStatus.CANCELLED,
                "requires_action": PaymentStatus.PENDING,
                "requires_payment_method": PaymentStatus.FAILED,
            }
            return status_map.get(intent.status, PaymentStatus.PENDING)
        except Exception:
            logger.exception("Plaid ACH payment verification failed")
            return PaymentStatus.FAILED

    def refund_payment(self, transaction_id, amount=None) -> RefundResult:
        try:
            params = {"payment_intent": transaction_id}
            if amount:
                params["amount"] = int(amount * 100)
            refund = self.stripe.Refund.create(**params)
            return RefundResult(success=True, refund_id=refund.id)
        except Exception as e:
            logger.exception("Plaid ACH refund failed")
            return RefundResult(success=False, error_message=str(e))

    def get_client_config(self) -> dict:
        try:
            from plaid.model.link_token_create_request import (
                LinkTokenCreateRequest,
            )
            from plaid.model.link_token_create_request_user import (
                LinkTokenCreateRequestUser,
            )

            request = LinkTokenCreateRequest(
                products=[self.Products("auth")],
                client_name="PropManager",
                country_codes=[self.CountryCode("US")],
                language="en",
                user=LinkTokenCreateRequestUser(client_user_id="propmanager"),
            )
            response = self.plaid_client.link_token_create(request)
            return {
                "link_token": response.link_token,
                "stripe_publishable_key": self.stripe_publishable_key,
            }
        except Exception as e:
            logger.exception("Failed to create Plaid link token")
            return {
                "error": str(e),
                "stripe_publishable_key": self.stripe_publishable_key,
            }

    def verify_webhook(self, request) -> dict:
        try:
            import stripe

            webhook_secret = self.config.config.get("stripe_webhook_secret", "")
            if not webhook_secret:
                raise ValueError(
                    "stripe_webhook_secret not configured for Plaid ACH gateway"
                )

            payload = request.body
            sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            # Extract transaction ID from event
            transaction_id = ""
            if event.data and event.data.object:
                transaction_id = getattr(event.data.object, "id", "")

            return {
                "valid": True,
                "event_type": event.type,
                "transaction_id": transaction_id,
                "raw_event": event.to_dict(),
            }
        except ValueError as e:
            logger.exception("Plaid ACH webhook payload invalid")
            raise
        except Exception as e:
            logger.exception("Plaid ACH webhook verification failed")
            raise ValueError(f"Webhook verification failed: {e}")

    def test_connection(self) -> tuple:
        errors = []

        # Test Plaid connection
        try:
            from plaid.model.institutions_get_by_id_request import (
                InstitutionsGetByIdRequest,
            )

            plaid_request = InstitutionsGetByIdRequest(
                institution_id="ins_109508",
                country_codes=[self.CountryCode("US")],
            )
            self.plaid_client.institutions_get_by_id(plaid_request)
        except Exception as e:
            errors.append(f"Plaid: {e}")

        # Test Stripe connection
        try:
            self.stripe.Account.retrieve()
        except Exception as e:
            errors.append(f"Stripe: {e}")

        if errors:
            return False, "; ".join(errors)
        return True, "Plaid and Stripe connections successful"
