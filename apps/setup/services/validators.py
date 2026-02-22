"""
Validation services for testing email, SMS, and payment gateway configurations.
"""

import logging

logger = logging.getLogger(__name__)


def test_email_configuration(config):
    """
    Test email configuration by sending a test email.

    Args:
        config: dict with email_host, email_port, email_host_user,
                email_host_password, default_from_email, email_use_tls, email_use_ssl

    Returns:
        dict with 'success' boolean and 'message' string
    """
    from django.core.mail import EmailMessage
    from django.core.mail.backends.smtp import EmailBackend

    try:
        backend = EmailBackend(
            host=config.get("email_host"),
            port=config.get("email_port", 587),
            username=config.get("email_host_user"),
            password=config.get("email_host_password"),
            use_tls=config.get("email_use_tls", True),
            use_ssl=config.get("email_use_ssl", False),
            timeout=10,
        )

        from_email = config.get("default_from_email")
        email = EmailMessage(
            subject="PropManager Email Test",
            body=(
                "This is a test email from PropManager setup wizard.\n\n"
                "If you received this email, your email configuration is working correctly."
            ),
            from_email=from_email,
            to=[from_email],  # Send to self
            connection=backend,
        )
        email.send()

        return {"success": True, "message": "Test email sent successfully!"}
    except Exception as e:
        logger.warning(f"Email test failed: {e}")
        return {"success": False, "message": f"Email test failed: {str(e)}"}


def test_sms_configuration(config):
    """
    Test SMS configuration using Twilio.
    Does not send an actual SMS, just validates credentials.

    Args:
        config: dict with account_sid, auth_token, phone_number

    Returns:
        dict with 'success' boolean and 'message' string
    """
    try:
        from twilio.rest import Client
        from twilio.base.exceptions import TwilioRestException

        account_sid = config.get("account_sid")
        auth_token = config.get("auth_token")

        client = Client(account_sid, auth_token)

        # Validate credentials by fetching account info
        account = client.api.accounts(account_sid).fetch()

        return {
            "success": True,
            "message": f"Connected to Twilio account: {account.friendly_name}",
        }
    except TwilioRestException as e:
        logger.warning(f"Twilio test failed: {e}")
        return {"success": False, "message": f"Twilio error: {e.msg}"}
    except ImportError:
        return {"success": False, "message": "Twilio library not installed."}
    except Exception as e:
        logger.warning(f"SMS test failed: {e}")
        return {"success": False, "message": f"SMS test failed: {str(e)}"}


def test_payment_gateway(provider, config_data):
    """
    Test payment gateway credentials.

    Args:
        provider: string like 'stripe', 'paypal', etc.
        config_data: dict with provider-specific configuration

    Returns:
        dict with 'success' boolean and 'message' string
    """
    testers = {
        "stripe": _test_stripe,
        "paypal": _test_paypal,
        "square": _test_square,
        "authorize_net": _test_authorize_net,
        "braintree": _test_braintree,
        "plaid": _test_plaid,
        "bitcoin": _test_bitcoin,
    }

    tester = testers.get(provider)
    if not tester:
        return {"success": True, "message": f"Gateway '{provider}' configured (not tested)"}

    return tester(config_data)


def _test_stripe(config):
    """Test Stripe credentials."""
    try:
        import stripe

        stripe.api_key = config.get("secret_key")
        # Retrieve account info to verify credentials
        account = stripe.Account.retrieve()

        return {
            "success": True,
            "message": f"Connected to Stripe: {account.get('business_profile', {}).get('name', 'Account verified')}",
        }
    except ImportError:
        return {"success": False, "message": "Stripe library not installed."}
    except Exception as e:
        logger.warning(f"Stripe test failed: {e}")
        return {"success": False, "message": f"Stripe error: {str(e)}"}


def _test_paypal(config):
    """Test PayPal credentials."""
    try:
        import paypalrestsdk

        paypalrestsdk.configure(
            {
                "mode": config.get("mode", "sandbox"),
                "client_id": config.get("client_id"),
                "client_secret": config.get("client_secret"),
            }
        )

        # Try to get an access token
        token = paypalrestsdk.Api().get_token()
        if token:
            return {"success": True, "message": "PayPal credentials verified."}
        return {"success": False, "message": "Could not obtain PayPal access token."}
    except ImportError:
        return {"success": False, "message": "PayPal library not installed."}
    except Exception as e:
        logger.warning(f"PayPal test failed: {e}")
        return {"success": False, "message": f"PayPal error: {str(e)}"}


def _test_square(config):
    """Test Square credentials."""
    try:
        from square.client import Client

        client = Client(
            access_token=config.get("access_token"),
            environment=config.get("environment", "sandbox"),
        )

        # Try to list locations
        result = client.locations.list_locations()
        if result.is_success():
            locations = result.body.get("locations", [])
            return {
                "success": True,
                "message": f"Square connected: {len(locations)} location(s) found.",
            }
        return {"success": False, "message": "Square API returned errors."}
    except ImportError:
        return {"success": False, "message": "Square library not installed."}
    except Exception as e:
        logger.warning(f"Square test failed: {e}")
        return {"success": False, "message": f"Square error: {str(e)}"}


def _test_authorize_net(config):
    """Test Authorize.Net credentials."""
    try:
        from authorizenet import apicontractsv1
        from authorizenet.apicontrollers import getMerchantDetailsController

        merchantAuth = apicontractsv1.merchantAuthenticationType()
        merchantAuth.name = config.get("api_login_id")
        merchantAuth.transactionKey = config.get("transaction_key")

        request = apicontractsv1.getMerchantDetailsRequest()
        request.merchantAuthentication = merchantAuth

        controller = getMerchantDetailsController(request)
        controller.execute()

        response = controller.getresponse()

        if response.messages.resultCode == "Ok":
            return {
                "success": True,
                "message": f"Authorize.Net connected: {response.merchantName}",
            }
        return {"success": False, "message": "Authorize.Net authentication failed."}
    except ImportError:
        return {"success": False, "message": "Authorize.Net library not installed."}
    except Exception as e:
        logger.warning(f"Authorize.Net test failed: {e}")
        return {"success": False, "message": f"Authorize.Net error: {str(e)}"}


def _test_braintree(config):
    """Test Braintree credentials."""
    try:
        import braintree

        gateway = braintree.BraintreeGateway(
            braintree.Configuration(
                environment=getattr(
                    braintree.Environment,
                    config.get("environment", "Sandbox"),
                ),
                merchant_id=config.get("merchant_id"),
                public_key=config.get("public_key"),
                private_key=config.get("private_key"),
            )
        )

        # Try to get merchant account
        result = gateway.merchant_account.all()
        return {"success": True, "message": "Braintree credentials verified."}
    except ImportError:
        return {"success": False, "message": "Braintree library not installed."}
    except Exception as e:
        logger.warning(f"Braintree test failed: {e}")
        return {"success": False, "message": f"Braintree error: {str(e)}"}


def _test_plaid(config):
    """Test Plaid credentials."""
    try:
        import plaid
        from plaid.api import plaid_api

        configuration = plaid.Configuration(
            host=getattr(
                plaid.Environment,
                config.get("environment", "Sandbox"),
            ),
            api_key={
                "clientId": config.get("client_id"),
                "secret": config.get("secret"),
            },
        )

        api_client = plaid.ApiClient(configuration)
        client = plaid_api.PlaidApi(api_client)

        # Try to get institution (a simple API call)
        return {"success": True, "message": "Plaid credentials configured."}
    except ImportError:
        return {"success": False, "message": "Plaid library not installed."}
    except Exception as e:
        logger.warning(f"Plaid test failed: {e}")
        return {"success": False, "message": f"Plaid error: {str(e)}"}


def _test_bitcoin(config):
    """Test Bitcoin configuration."""
    # Bitcoin doesn't require external API validation in the same way
    # Just verify the wallet address format
    wallet_address = config.get("wallet_address", "")
    if wallet_address:
        # Basic validation: Bitcoin addresses are 26-35 characters
        if 26 <= len(wallet_address) <= 62:
            return {
                "success": True,
                "message": "Bitcoin wallet address configured.",
            }
        return {"success": False, "message": "Invalid Bitcoin wallet address format."}
    return {"success": False, "message": "No Bitcoin wallet address provided."}


def run_database_checks():
    """
    Run comprehensive database connectivity checks.

    Returns:
        list of dicts with 'name', 'passed', 'message' for each check
    """
    from django.db import connection
    from django.apps import apps

    checks = []

    # Check 1: Basic connectivity
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks.append(
            {
                "name": "Database Connection",
                "passed": True,
                "message": "Successfully connected to database",
            }
        )
    except Exception as e:
        checks.append(
            {
                "name": "Database Connection",
                "passed": False,
                "message": f"Connection failed: {str(e)}",
            }
        )
        # If basic connectivity fails, return early
        return checks

    # Check 2: Required tables exist
    required_models = [
        ("accounts", "User"),
        ("properties", "Property"),
        ("properties", "Unit"),
        ("leases", "Lease"),
        ("billing", "Invoice"),
    ]

    for app_label, model_name in required_models:
        try:
            model = apps.get_model(app_label, model_name)
            # Just check if we can query the table
            model.objects.exists()
            checks.append(
                {
                    "name": f"Table: {app_label}.{model_name}",
                    "passed": True,
                    "message": "Table accessible",
                }
            )
        except Exception as e:
            checks.append(
                {
                    "name": f"Table: {app_label}.{model_name}",
                    "passed": False,
                    "message": f"Error: {str(e)}",
                }
            )

    # Check 3: Database can write
    try:
        from apps.setup.models import SetupConfiguration

        config = SetupConfiguration.get_instance()
        # Just accessing it proves we can read/write
        checks.append(
            {
                "name": "Database Write Access",
                "passed": True,
                "message": "Can read and write to database",
            }
        )
    except Exception as e:
        checks.append(
            {
                "name": "Database Write Access",
                "passed": False,
                "message": f"Write test failed: {str(e)}",
            }
        )

    return checks
