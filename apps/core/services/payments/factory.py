import logging

logger = logging.getLogger(__name__)

GATEWAY_MAP = {
    "stripe": "apps.core.services.payments.stripe.StripeGateway",
    "paypal": "apps.core.services.payments.paypal.PayPalGateway",
    "square": "apps.core.services.payments.square.SquareGateway",
}


def get_gateway_class(provider):
    from django.utils.module_loading import import_string
    path = GATEWAY_MAP.get(provider)
    if not path:
        raise ValueError(f"Unknown payment provider: {provider}")
    return import_string(path)


def get_active_gateway():
    from apps.billing.models import PaymentGatewayConfig
    config = PaymentGatewayConfig.objects.filter(is_active=True, is_default=True).first()
    if not config:
        logger.warning("No active default payment gateway configured")
        return None
    cls = get_gateway_class(config.provider)
    return cls(config)


def get_gateway_for_provider(provider):
    from apps.billing.models import PaymentGatewayConfig
    config = PaymentGatewayConfig.objects.filter(provider=provider, is_active=True).first()
    if not config:
        return None
    cls = get_gateway_class(provider)
    return cls(config)
