# API & Services

## Payment Gateway Architecture

PropManager uses a pluggable adapter pattern for payment processing. Gateways are configured through the admin UI (no code changes needed to switch providers).

### Overview

```
Tenant Payment → get_active_gateway() → StripeGateway / PayPalGateway / SquareGateway
                        ↑
                PaymentGatewayConfig
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
```

### Available Gateways

| Provider | Module | Config Keys |
|---|---|---|
| Stripe | `apps.core.services.payments.stripe` | `secret_key`, `publishable_key`, `webhook_secret` |
| PayPal | `apps.core.services.payments.paypal` | `client_id`, `client_secret`, `mode` (sandbox/live) |
| Square | `apps.core.services.payments.square` | `access_token`, `environment`, `location_id` |

### Configuration

Gateways are configured via the admin portal at `/admin-portal/billing/settings/`:

1. Select a provider (Stripe, PayPal, or Square)
2. Enter API credentials in the config JSON field
3. Set as active and/or default
4. Only one gateway can be the default at a time

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

## Template Tags

Custom template tags available via `{% load core_tags %}`:

| Tag/Filter | Usage | Description |
|---|---|---|
| `currency` | `{{ amount\|currency }}` | Formats as `$1,234.56` |
| `phone_format` | `{{ phone\|phone_format }}` | Formats phone numbers |
| `human_filesize` | `{{ size\|human_filesize }}` | Formats bytes as KB/MB/GB |
| `active_nav` | `{% active_nav request 'path' %}` | Returns "active" for current nav item |
