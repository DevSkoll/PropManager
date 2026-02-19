# API & Services

## Payment Gateway Architecture

PropManager uses a pluggable adapter pattern for payment processing. Gateways are configured through the admin UI (no code changes needed to switch providers).

### Overview

```
Tenant Payment → get_active_gateway() → StripeGateway / PayPalGateway / SquareGateway
                        ↑                 AuthorizeNetGateway / BraintreeGateway
                PaymentGatewayConfig       PlaidAchGateway / BitcoinGateway
                (DB: API keys, settings)
```

### Abstract Interface

All gateways implement `apps.core.services.payments.base.PaymentGateway`:

```python
class PaymentGateway(ABC):
    def create_payment(self, amount, currency, metadata) -> PaymentResult
    def verify_payment(self, transaction_id) -> PaymentStatus
    def refund_payment(self, transaction_id, amount) -> RefundResult
    def get_client_config(self) -> dict  # Frontend SDK initialization
    def verify_webhook(self, request) -> dict  # Webhook signature verification
    def test_connection(self) -> tuple[bool, str]  # Credential validation
```

### Available Gateways

| Provider | Module | Config Keys |
|---|---|---|
| Stripe | `apps.core.services.payments.stripe` | `secret_key`, `publishable_key`, `webhook_secret` |
| PayPal | `apps.core.services.payments.paypal` | `client_id`, `client_secret`, `mode`, `webhook_id` |
| Square | `apps.core.services.payments.square` | `access_token`, `application_id`, `location_id`, `environment`, `webhook_signature_key`, `webhook_url` |
| Authorize.Net | `apps.core.services.payments.authorizenet` | `api_login_id`, `transaction_key`, `signature_key`, `client_key`, `environment` |
| Braintree | `apps.core.services.payments.braintree_gw` | `merchant_id`, `public_key`, `private_key`, `environment` |
| Plaid + ACH | `apps.core.services.payments.plaid_ach` | `plaid_client_id`, `plaid_secret`, `plaid_environment`, `stripe_secret_key`, `stripe_publishable_key` |
| Bitcoin | `apps.core.services.payments.bitcoin` | `xpub`, `network`, `payment_window_minutes`, `required_confirmations` |

### Configuration

Gateways are configured via the admin portal at `/admin-portal/billing/settings/`:

1. Click "Add Gateway" and select a provider
2. Fill in the guided, provider-specific config form (labeled fields with help text)
3. Set as active and/or default
4. Only one gateway can be the default at a time
5. Use "Test Connection" to verify credentials

### Webhook Security

All gateways (except Bitcoin) support webhook signature verification via `verify_webhook()`. Inbound webhooks are logged in the `WebhookEvent` model for audit. Events are deduplicated by `event_id`. View the webhook log at `/admin-portal/billing/settings/webhooks/`.

### Factory Pattern

```python
from apps.core.services.payments.factory import get_active_gateway

gateway = get_active_gateway()        # Returns default active gateway
result = gateway.create_payment(
    amount=Decimal("1200.00"),
    currency="usd",
    metadata={"invoice_id": str(invoice.pk)}
)
```

### Bitcoin Gateway

The Bitcoin gateway uses a locally managed HD wallet with xpub-only keys on the server (private key stays offline).

**Architecture:**
- Address derivation: `bitcoinlib` HDKey from xpub at incrementing BIP32 indexes
- Payment monitoring: Django-Q2 task polls `mempool.space` API every 2 minutes
- Price tracking: CoinGecko API with 5-minute Django cache TTL
- Models: `BitcoinWalletConfig`, `BitcoinPayment`, `BitcoinPriceSnapshot`

**Payment Flow:**
1. Tenant selects Bitcoin payment → system derives unique address, snapshots BTC-USD rate
2. Tenant sees QR code + address + expected BTC amount + countdown timer
3. Background task monitors `mempool.space` for incoming transactions
4. On confirmation (>= `required_confirmations`): creates `Payment` record, updates `Invoice`
5. Admin can transfer BTC out at `/admin-portal/billing/bitcoin/transfer/`

**Admin Dashboard:** `/admin-portal/billing/bitcoin/` — wallet balance, pending payments, transfer controls.

---

## SMS Service (Twilio)

Located at `apps.core.services.sms`.

### Configuration

Set these environment variables:

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+15551234567
```

### Usage

```python
from apps.core.services.sms import sms_service

sms_service.send_sms(
    to="+15559876543",
    body="Your OTP code is 123456"
)
```

In development, if Twilio credentials are not set, SMS operations will log to the console instead of sending.

### Future: Voice/AI Integration

The SMS service is designed as an extensible adapter. Future plans include:
- Twilio Voice integration for tenant phone calls
- AI-powered voice interaction for common requests (maintenance, billing inquiries)
- Call monitoring and transcription

---

## Email Service

Located at `apps.core.services.email`.

### Configuration

Development uses Django's console email backend (prints to terminal). For production:

```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=app_password
DEFAULT_FROM_EMAIL=noreply@propmanager.com
```

### Usage

```python
from apps.core.services.email import send_email

send_email(
    subject="Your Invoice is Ready",
    body="Your rent invoice for March has been issued.",
    to=["tenant@example.com"],
    html_message="<h1>Invoice Ready</h1><p>...</p>"  # optional
)
```

---

## Weather Service (OpenWeatherMap)

Located at `apps.core.services.weather`.

### Configuration

```
OPENWEATHERMAP_API_KEY=your_api_key
```

Get a free API key at [openweathermap.org](https://openweathermap.org/api).

### How It Works

1. **Admin configures** weather monitoring per property (`/admin-portal/weather/`)
   - Set latitude/longitude
   - Define alert thresholds (snow inches, wind mph, temperature limits)

2. **Django-Q2 polls** OpenWeatherMap every 2 hours for each active property

3. **Snapshots stored** in `WeatherSnapshot` model with full API response

4. **Thresholds checked** automatically:
   - Snow > X inches → Snow alert
   - Wind > Y mph → Wind alert
   - Temperature < low threshold → Extreme cold alert
   - Temperature > high threshold → Extreme heat alert

5. **Alerts generated** as `WeatherAlert` records with severity levels:
   - **Watch** - Minor threshold breach
   - **Warning** - Significant conditions
   - **Emergency** - Dangerous conditions

6. **Notifications sent** to all tenants at the affected property via in-app notifications (and optionally SMS)

### Usage

```python
from apps.core.services.weather import weather_service

data = weather_service.get_current_weather(lat=34.0522, lon=-118.2437)
# Returns: {
#   "temperature_f": 72.5,
#   "feels_like_f": 70.1,
#   "humidity": 45,
#   "wind_speed_mph": 8.2,
#   "conditions": [...],
#   "snow_inches": 0,
#   "rain_inches": 0,
#   ...
# }
```

---

## Marketing Campaign Service

### Campaign Lifecycle

```
Draft → Scheduled/Sending → Sent
  │                           │
  └──→ Cancelled ←────────────┘
```

### Segmentation

Campaigns target tenants using filter segments:

| Filter Type | Description | Filter Value |
|---|---|---|
| `all` | All active tenants | `{}` |
| `by_property` | Tenants at a specific property | `{"property_id": "<uuid>"}` |
| `by_lease_status` | Tenants with matching lease status | `{"status": "active"}` |
| `by_move_in_date` | Tenants who moved in within a date range | `{"start": "2025-01-01", "end": "2025-12-31"}` |

Multiple segments per campaign are unioned together.

### Email Tracking

- **Open tracking**: 1x1 transparent GIF pixel appended to HTML emails
  - Endpoint: `/admin-portal/marketing/track/open/<recipient_pk>/`
- **Click tracking**: URLs in email body are replaced with redirect links
  - Endpoint: `/admin-portal/marketing/track/click/<tracking_token>/`
  - Atomic `F()` increment on `CampaignLink.click_count`

### Sending

Campaigns are sent via Django-Q2 async tasks:

1. `send_campaign(campaign_id)` - Orchestrator
2. `generate_campaign_recipients(campaign_id)` - Resolves segments → creates recipient records
3. `send_campaign_email(recipient_id)` - Sends individual email with tracking injected

---

## Reward Service

Located at `apps.rewards.services.RewardService`. All mutating methods use `select_for_update()` + `transaction.atomic()`.

### Credits vs Rewards

| | Credits | Rewards |
|---|---|---|
| **Source** | Tenant overpayments (real money) | Promotional grants (not real money) |
| **Model** | `PrepaymentCredit` | `RewardBalance` + `RewardTransaction` |
| **Payment method** | `Payment(method="credit")` | `Payment(method="reward")` |
| **Apply order** | First (real money priority) | Second (after credits) |

### Methods

```python
from apps.rewards.services import RewardService

# Get or create a tenant's reward balance
balance = RewardService.get_or_create_balance(tenant)

# Grant a reward (creates transaction, dispatches notification)
txn = RewardService.grant_reward(
    tenant=tenant,
    amount=Decimal("50.00"),
    transaction_type="manual_grant",  # or streak_earned, prepayment_earned
    description="Welcome bonus",
    granted_by=admin_user,  # optional
)

# Apply rewards to an invoice
payment = RewardService.apply_rewards_to_invoice(
    invoice=invoice,
    amount=Decimal("25.00"),  # None = apply full balance up to balance_due
    applied_by=user,
)

# Reverse a reward payment
txn = RewardService.reverse_reward_application(payment)

# Admin balance adjustment (+/-)
txn = RewardService.admin_adjust_balance(
    tenant=tenant,
    amount=Decimal("-10.00"),  # negative to deduct
    description="Correction",
    adjusted_by=admin_user,
)

# Evaluate streak rewards for a tenant at a property
granted = RewardService.evaluate_streak_rewards(tenant, property_obj)

# Evaluate prepayment rewards after an overpayment
granted = RewardService.evaluate_prepayment_rewards(
    tenant, property_obj, overpayment_amount
)
```

### Streak Evaluation Algorithm

1. Get `PropertyRewardsConfig` — bail if rewards or streak not enabled
2. Get/create `StreakEvaluation` for tenant + config
3. Walk each month from `last_evaluated_month + 1` to last completed month
4. For each month: find invoices, check if paid on or before `due_date`
5. On-time → increment `current_streak_months`; late/unpaid → reset to 0
6. Check all `StreakRewardTier`s — grant if streak >= `months_required`
7. Non-recurring tiers: skip if already in `awarded_tier_ids`
8. Recurring tiers: grant `streak // months_required` times total (minus already granted)

### Integration Points

- **Prepayment hook**: `PaymentService.record_manual_payment()` calls `evaluate_prepayment_rewards()` when an overpayment creates a `PrepaymentCredit`
- **Payment initiation**: `tenant_initiate_payment` view applies rewards (checkbox) before credits and gateway
- **Billing dashboard**: Displays reward balance alongside account credit
- **Notifications**: `grant_reward()` dispatches `reward_earned` event via `dispatch_event()`

---

## Template Tags

Custom template tags available via `{% load core_tags %}`:

| Tag/Filter | Usage | Description |
|---|---|---|
| `currency` | `{{ amount\|currency }}` | Formats as `$1,234.56` |
| `phone_format` | `{{ phone\|phone_format }}` | Formats phone numbers |
| `human_filesize` | `{{ size\|human_filesize }}` | Formats bytes as KB/MB/GB |
| `active_nav` | `{% active_nav request 'path' %}` | Returns "active" for current nav item |
