import logging
from datetime import timedelta
from decimal import Decimal

import requests
from django.db import transaction
from django.utils import timezone

from .base import PaymentGateway, PaymentResult, PaymentStatus, RefundResult
from .bitcoin_utils import (
    derive_address_from_xpub,
    get_btc_usd_rate,
    satoshis_to_btc,
    usd_to_satoshis,
)

logger = logging.getLogger(__name__)

MEMPOOL_API_BASE = "https://mempool.space/api"


class BitcoinGateway(PaymentGateway):
    def __init__(self, config):
        super().__init__(config)
        self.xpub = config.config.get("xpub", "")
        self.network = config.config.get("network", "bitcoin")
        self.payment_window_minutes = int(
            config.config.get("payment_window_minutes", 60)
        )
        self.required_confirmations = int(
            config.config.get("required_confirmations", 1)
        )

    def create_payment(self, amount, currency, metadata) -> PaymentResult:
        try:
            from apps.billing.models import BitcoinPayment, BitcoinWalletConfig

            # Get current exchange rate
            btc_usd_rate = get_btc_usd_rate()
            usd_amount = Decimal(str(amount))
            expected_satoshis = usd_to_satoshis(usd_amount, btc_usd_rate)

            # Get or create wallet config for this gateway
            wallet_config, _ = BitcoinWalletConfig.objects.get_or_create(
                payment_gateway_config=self.config,
                defaults={
                    "xpub": self.xpub,
                    "network": self.network,
                    "next_index": 0,
                },
            )

            # Derive next address and atomically increment the index
            with transaction.atomic():
                wallet_config = BitcoinWalletConfig.objects.select_for_update().get(
                    pk=wallet_config.pk
                )
                index = wallet_config.next_index
                btc_address = derive_address_from_xpub(
                    self.xpub, index, self.network
                )
                wallet_config.next_index = index + 1
                wallet_config.save(update_fields=["next_index"])

            # Create the BitcoinPayment record
            expires_at = timezone.now() + timedelta(
                minutes=self.payment_window_minutes
            )
            invoice = metadata.get("invoice")

            btc_payment = BitcoinPayment.objects.create(
                invoice=invoice,
                btc_address=btc_address,
                derivation_index=index,
                status="pending",
                usd_amount=usd_amount,
                btc_usd_rate=btc_usd_rate,
                expected_satoshis=expected_satoshis,
                expires_at=expires_at,
            )

            return PaymentResult(
                success=True,
                transaction_id=btc_address,
                status=PaymentStatus.PENDING,
                raw_response={
                    "btc_address": btc_address,
                    "expected_satoshis": expected_satoshis,
                    "btc_amount": str(satoshis_to_btc(expected_satoshis)),
                    "btc_usd_rate": str(btc_usd_rate),
                    "expires_at": expires_at.isoformat(),
                    "payment_id": btc_payment.pk,
                },
            )
        except Exception as e:
            logger.exception("Bitcoin payment creation failed")
            return PaymentResult(success=False, error_message=str(e))

    def verify_payment(self, transaction_id) -> PaymentStatus:
        try:
            from apps.billing.models import BitcoinPayment

            btc_payment = BitcoinPayment.objects.get(btc_address=transaction_id)

            # Check if expired
            if btc_payment.is_expired():
                btc_payment.status = "expired"
                btc_payment.save(update_fields=["status"])
                return PaymentStatus.CANCELLED

            # Query mempool.space for address info
            url = f"{MEMPOOL_API_BASE}/address/{transaction_id}"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()

            chain_stats = data.get("chain_stats", {})
            mempool_stats = data.get("mempool_stats", {})

            funded_confirmed = chain_stats.get("funded_txo_sum", 0)
            funded_mempool = mempool_stats.get("funded_txo_sum", 0)
            tx_count = chain_stats.get("tx_count", 0)

            total_received = funded_confirmed + funded_mempool
            btc_payment.received_satoshis = total_received

            if funded_confirmed >= btc_payment.expected_satoshis and tx_count >= self.required_confirmations:
                # Payment confirmed on-chain with enough confirmations
                btc_payment.status = "confirmed"
                btc_payment.confirmations = tx_count
                btc_payment.confirmed_at = timezone.now()
                btc_payment.save(
                    update_fields=[
                        "received_satoshis",
                        "status",
                        "confirmations",
                        "confirmed_at",
                    ]
                )
                return PaymentStatus.COMPLETED
            elif total_received > 0 and funded_confirmed < btc_payment.expected_satoshis:
                # Transaction is in mempool but not yet confirmed
                btc_payment.status = "mempool"
                btc_payment.confirmations = tx_count
                btc_payment.save(
                    update_fields=["received_satoshis", "status", "confirmations"]
                )
                return PaymentStatus.PENDING
            else:
                # No funds received yet
                btc_payment.save(update_fields=["received_satoshis"])
                return PaymentStatus.PENDING

        except Exception:
            logger.exception("Bitcoin payment verification failed")
            return PaymentStatus.FAILED

    def refund_payment(self, transaction_id, amount=None) -> RefundResult:
        return RefundResult(
            success=False,
            error_message=(
                "Bitcoin refunds require manual processing. "
                "Please transfer BTC manually from the admin dashboard."
            ),
        )

    def get_client_config(self) -> dict:
        try:
            btc_usd_rate = get_btc_usd_rate()
            config = {
                "btc_usd_rate": str(btc_usd_rate),
                "payment_window_minutes": self.payment_window_minutes,
                "required_confirmations": self.required_confirmations,
                "network": self.network,
            }
            return config
        except Exception as e:
            logger.exception("Failed to build Bitcoin client config")
            return {"error": str(e)}

    def verify_webhook(self, request) -> dict:
        return {
            "valid": True,
            "event_type": "poll_check",
            "transaction_id": "",
            "raw_event": {},
        }

    def test_connection(self) -> tuple:
        errors = []

        # Test xpub derivation
        try:
            address = derive_address_from_xpub(self.xpub, 0, self.network)
            if not address:
                errors.append("xpub derivation returned empty address")
        except Exception as e:
            errors.append(f"xpub derivation failed: {e}")

        # Test mempool.space connectivity
        try:
            response = requests.get(
                f"{MEMPOOL_API_BASE}/v1/fees/recommended", timeout=10
            )
            response.raise_for_status()
        except Exception as e:
            errors.append(f"mempool.space unreachable: {e}")

        if errors:
            return False, "; ".join(errors)
        return True, "Connection successful"
