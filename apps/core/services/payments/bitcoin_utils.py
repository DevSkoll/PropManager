import base64
import hashlib
import logging
from decimal import Decimal

import requests
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
)
BTC_USD_CACHE_KEY = "btc_usd_rate"
BTC_USD_CACHE_TTL = 300  # 5 minutes


def get_btc_usd_rate() -> Decimal:
    """Fetch the current BTC-USD rate.

    Uses Django cache with a 5-minute TTL. Falls back to the most recent
    BitcoinPriceSnapshot if the CoinGecko API is unreachable.
    """
    cached = cache.get(BTC_USD_CACHE_KEY)
    if cached is not None:
        return Decimal(str(cached))

    try:
        response = requests.get(COINGECKO_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        rate = Decimal(str(data["bitcoin"]["usd"]))
        cache.set(BTC_USD_CACHE_KEY, str(rate), BTC_USD_CACHE_TTL)
        return rate
    except Exception:
        logger.exception("Failed to fetch BTC-USD rate from CoinGecko")

    # Fall back to last known rate from database
    try:
        from apps.billing.models import BitcoinPriceSnapshot

        snapshot = BitcoinPriceSnapshot.objects.first()  # ordered by -created_at
        if snapshot:
            logger.warning(
                "Using last known BTC-USD rate from BitcoinPriceSnapshot: %s",
                snapshot.btc_usd_rate,
            )
            return snapshot.btc_usd_rate
    except Exception:
        logger.exception("Failed to fetch fallback BTC-USD rate from database")

    raise RuntimeError("Unable to determine BTC-USD exchange rate")


def usd_to_satoshis(usd_amount: Decimal, btc_usd_rate: Decimal) -> int:
    """Convert a USD amount to satoshis given the current BTC-USD rate."""
    return int((usd_amount / btc_usd_rate) * 100_000_000)


def satoshis_to_btc(satoshis: int) -> Decimal:
    """Convert satoshis to BTC."""
    return Decimal(satoshis) / Decimal("100000000")


def _get_fernet() -> Fernet:
    """Build a Fernet instance from the BITCOIN_ENCRYPTION_KEY setting."""
    encryption_key = getattr(settings, "BITCOIN_ENCRYPTION_KEY", None)
    if not encryption_key:
        raise ValueError(
            "BITCOIN_ENCRYPTION_KEY is not set in Django settings. "
            "Cannot encrypt or decrypt Bitcoin keys."
        )
    # Derive a 32-byte key from the setting value so any passphrase works
    key_bytes = hashlib.sha256(encryption_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_key(plaintext: str) -> str:
    """Encrypt a string using Fernet. Returns a base64-encoded ciphertext."""
    f = _get_fernet()
    token = f.encrypt(plaintext.encode())
    return base64.urlsafe_b64encode(token).decode()


def decrypt_key(ciphertext: str) -> str:
    """Decrypt a base64-encoded Fernet ciphertext back to plaintext."""
    f = _get_fernet()
    token = base64.urlsafe_b64decode(ciphertext.encode())
    return f.decrypt(token).decode()


def derive_address_from_xpub(
    xpub: str, index: int, network: str = "bitcoin"
) -> str:
    """Derive a bech32 (bc1q) address from an xpub at the given index.

    Uses bitcoinlib HDKey to derive a child key and return its segwit address.
    """
    from bitcoinlib.keys import HDKey

    network_name = "bitcoin" if network == "bitcoin" else "testnet"
    hd_key = HDKey(xpub, network=network_name)
    child_key = hd_key.subkey_for_path(f"0/{index}")
    return child_key.address(witness_type="segwit")
