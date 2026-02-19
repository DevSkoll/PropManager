# Architecture Overview

## Default Development Accounts

Run `python manage.py seed_dev_data` to create these accounts and sample data.

### Admin Portal (`/admin-portal/login/`)

| Username | Password | Role | Description |
|---|---|---|---|
| `admin` | `admin123` | Admin | Full access, superuser, Django admin |
| `staff` | `staff123` | Staff | Full admin portal access |

### Tenant Portal (`/tenant/login/`)

Tenants use passwordless OTP in production. In development, the OTP code is always **`123456`** (configured via `DEV_OTP_CODE` in `config/settings/development.py`).

| Email | Password | Name | Unit |
|---|---|---|---|
| `tenant1@example.com` | `tenant123` | Jane Smith | Sunset Apts #101 |
| `tenant2@example.com` | `tenant123` | Bob Johnson | Sunset Apts #102 |
| `tenant3@example.com` | `tenant123` | Maria Garcia | Sunset Apts #103 |
| `tenant4@example.com` | `tenant123` | David Williams | Sunset Apts #104 |
| `tenant5@example.com` | `tenant123` | Sarah Brown | Sunset Apts #105 |

### Django Admin (`/django-admin/`)

| Username | Password |
|---|---|
| `admin` | `admin123` |

### Contractor Access

No accounts needed. Admins generate unique token URLs when assigning contractors to work orders (e.g., `/contractor/<token>/`). Tokens expire after 30 days by default.

---

## System Design

PropManager is a Django monolith with 11 apps, each owning a specific domain. The application serves three distinct user types through separate portals.

```
                    ┌─────────────────────────────────────────┐
                    │              NGINX / Reverse Proxy       │
                    └─────┬──────────────┬──────────────┬─────┘
                          │              │              │
                   /tenant/*     /admin-portal/*   /contractor/*
                          │              │              │
                    ┌─────▼──────────────▼──────────────▼─────┐
                    │            Django Application            │
                    │                                          │
                    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
                    │  │  Tenant  │ │  Admin   │ │Contractor│ │
                    │  │  Portal  │ │  Portal  │ │  Portal  │ │
                    │  └────┬─────┘ └────┬─────┘ └────┬─────┘ │
                    │       │            │            │        │
                    │  ┌────▼────────────▼────────────▼────┐  │
                    │  │        10 Django Apps              │  │
                    │  │  accounts · properties · leases    │  │
                    │  │  billing · workorders · comms      │  │
                    │  │  documents · weather · marketing   │  │
                    │  │  core (services, middleware)       │  │
                    │  └────┬──────────────────────────┬───┘  │
                    │       │                          │       │
                    │  ┌────▼────┐              ┌──────▼────┐  │
                    │  │Database │              │ Django-Q2 │  │
                    │  │SQLite/PG│              │ Workers   │  │
                    │  └─────────┘              └───────────┘  │
                    └──────────────────────────────────────────┘
                                      │
                          ┌───────────┼───────────┐
                          ▼           ▼           ▼
                      Twilio     OpenWeather   Stripe/
                       SMS         Map         PayPal/
                                               Square
```

## Data Model Overview

41 models across 11 apps. All models use UUID primary keys via the `TimeStampedModel` abstract base.

### Core (`apps/core`)

```
TimeStampedModel (abstract)
├── id: UUID (primary key)
├── created_at: DateTime (auto, indexed)
└── updated_at: DateTime (auto)

AuditMixin (abstract)
├── created_by: FK → User (nullable)
└── updated_by: FK → User (nullable)
```

### Accounts (`apps/accounts`) - 5 models

```
User (extends AbstractUser)
├── id: UUID
├── role: tenant | admin | staff
├── phone_number, is_phone_verified, is_email_verified
├── preferred_contact: email | sms
├──→ TenantProfile (1:1) - emergency contact, move_in_date, notes
├──→ AdminProfile (1:1) - otp_enabled, otp_delivery
└──→ OTPToken (1:N) - code, purpose, expires_at, is_used

ContractorAccessToken
├── token: unique URL-safe string (64 chars)
├── contractor_name, phone, email
├── work_order: FK → WorkOrder
├── expires_at, is_revoked
└── last_accessed_at
```

### Properties (`apps/properties`) - 4 models

```
Property
├── name, property_type, address fields
├── total_units, is_active
└──→ Unit (1:N)
     ├── unit_number, bedrooms, bathrooms, square_feet
     ├── base_rent, status (vacant/occupied/maintenance)
     └──→ UnitAmenity (N:M via through table) → Amenity
```

### Leases (`apps/leases`) - 3 models

```
Lease
├── unit: FK → Unit (PROTECT)
├── tenant: FK → User (PROTECT)
├── status: draft | active | expired | terminated | renewed
├── lease_type: fixed | month_to_month
├── start_date, end_date, monthly_rent, security_deposit
├──→ LeaseTerm (1:N) - custom clauses
└──→ LeaseTermination (1:1) - early termination details
```

### Billing (`apps/billing`) - 6 models

```
PaymentGatewayConfig
├── provider: stripe | paypal | square
├── is_active, is_default
├── config: JSON (API keys)
└── supported_methods: JSON

Invoice
├── invoice_number (unique), lease, tenant
├── status: draft | issued | paid | partial | overdue | cancelled
├── issue_date, due_date, total_amount, amount_paid
├──→ InvoiceLineItem (1:N) - charge_type, qty, unit_price, amount
└──→ Payment (1:N) - amount, method, status, gateway details

PrepaymentCredit
├── tenant, amount, remaining_amount
└── source_payment: FK → Payment
```

### Rewards (`apps/rewards`) - 6 models

Tenant rewards program — promotional discounts (NOT real money), tracked separately from prepayment credits with distinct audit trails.

```
PropertyRewardsConfig (1:1 → Property)
├── rewards_enabled, streak_reward_enabled, prepayment_reward_enabled
├── prepayment_threshold_amount, prepayment_reward_amount
├── auto_apply_rewards
└──→ StreakRewardTier (1:N)
     ├── months_required, reward_amount, is_recurring
     └── unique_together: (config, months_required)

RewardBalance (1:1 → User)
├── balance, total_earned, total_redeemed

RewardTransaction (immutable audit trail)
├── tenant, transaction_type, amount, balance_after, description
├── type: streak_earned | prepayment_earned | manual_grant | redeemed | reversed | admin_adjustment | expired
├── invoice (nullable), payment (nullable), streak_tier (nullable)
└── AuditMixin (created_by, updated_by)

StreakEvaluation (unique: tenant + config)
├── current_streak_months, last_evaluated_month
├── streak_broken_at, awarded_tier_ids (JSON)

PrepaymentRewardTracker (unique: tenant + config)
├── cumulative_prepayment, rewards_granted_count
```

### Work Orders (`apps/workorders`) - 4 models

```
WorkOrder
├── title, description, unit, reported_by
├── status: created → verified → assigned → in_progress → completed → closed
├── priority: low | medium | high | emergency
├── category: plumbing | electrical | hvac | ...
├──→ ContractorAssignment (1:N) - links to ContractorAccessToken
├──→ WorkOrderNote (1:N) - text, is_internal, dual author fields
└──→ WorkOrderImage (1:N) - image file, caption
```

**Status State Machine:**
```
created → verified → assigned → in_progress → completed → closed
  │          │          │           │                        ▲
  └──────────┴──────────┴───────────┴────────────────────────┘
                    (any status → closed)
```

### Communications (`apps/communications`) - 4 models

```
MessageThread
├── subject, is_closed
├── participants: M2M → User
├── related_work_order: FK → WorkOrder (optional)
└──→ Message (1:N) - sender, body, is_read, read_at

Notification
├── recipient, channel (in_app/email/sms)
├── category, title, body, is_read, action_url

Announcement
├── title, body, author
├── property (optional - null = all properties)
└── is_published, published_at
```

### Documents (`apps/documents`) - 2 models

```
Document
├── title, document_type, file, file_size, mime_type
├── category: FK → DocumentCategory
├── Nullable FKs: property, unit, lease, tenant, work_order
└── is_tenant_visible: boolean
```

### Weather (`apps/weather`) - 3 models

```
WeatherMonitorConfig (1:1 → Property)
├── latitude, longitude, is_active
├── polling_interval_hours
└── thresholds: snow, wind, temp_low, temp_high

WeatherSnapshot
├── property, timestamp, temperature_f, humidity, wind_speed_mph
├── snow_inches, rain_inches, conditions (JSON)
└── raw_data: JSON (full API response)

WeatherAlert
├── property, snapshot
├── alert_type: snow | storm | extreme_heat | extreme_cold | wind | flood
├── severity: watch | warning | emergency
└── notification_sent, sent_at
```

### Marketing (`apps/marketing`) - 4 models

```
Campaign
├── name, subject, body_html, body_text
├── status: draft | scheduled | sending | sent | cancelled
├── scheduled_at, sent_at, created_by
├──→ CampaignSegment (1:N) - filter_type, filter_value (JSON)
├──→ CampaignRecipient (1:N) - tenant, status, tracking timestamps
└──→ CampaignLink (1:N) - original_url, tracking_token, click_count
```

## Authentication Flows

### Tenant - Passwordless OTP

```
1. Tenant enters email or phone number
2. System looks up user, generates 6-digit OTP (10 min expiry)
3. OTP sent via email (console in dev) or SMS (Twilio)
4. Tenant enters OTP code
5. System validates → creates Django session
```

- Rate limited to 5 OTP requests per hour per user
- Previous unused OTPs are invalidated on new generation
- Custom `PasswordlessOTPBackend` in `accounts/backends.py`

### Admin - Password + Optional 2FA

```
1. Admin enters username + password
2. Django ModelBackend validates credentials
3. If AdminProfile.otp_enabled:
   a. Generate OTP, send via configured method
   b. Admin enters OTP code
   c. Validate → session
4. If OTP not enabled: immediate session
```

### Contractor - Token Access

```
1. Admin assigns contractor to work order
2. System generates unique URL-safe token (48 bytes)
3. Admin shares link: /contractor/<token>/
4. Contractor clicks link → token validated (not expired/revoked)
5. Scoped access to assigned work order only
```

- No Django session created
- Token attached to `request.contractor_token` via decorator
- Contractors can: view details, update status, add notes, upload photos
- Default expiry: 30 days, configurable per assignment

## Middleware & Access Control

### RoleBasedAccessMiddleware

Routes are protected based on URL prefix:

| URL Prefix | Required Role | Redirect on Unauthorized |
|---|---|---|
| `/tenant/*` | `tenant` | `/tenant/login/` |
| `/admin-portal/*` | `admin` or `staff` | `/admin-portal/login/` |
| `/contractor/*` | No auth (token-based) | N/A |

Exempted paths: login URLs, OTP verify URLs, static/media files.

### Decorators

- `@tenant_required` - Validates user.role == "tenant"
- `@admin_required` - Validates user.role in ("admin", "staff")
- `@contractor_token_required` - Validates ContractorAccessToken from URL

## Background Tasks

Django-Q2 is used for async task processing with ORM-backed broker:

| Task | Schedule | Description |
|---|---|---|
| `poll_weather_for_all_properties` | Every 2 hours | Fetch weather data, check thresholds, generate alerts |
| `process_scheduled_campaigns` | Every 5 minutes | Send campaigns whose scheduled_at has passed |
| `check_overdue_invoices` | Daily | Mark overdue invoices, send notifications |
| `cleanup_old_snapshots` | Weekly | Remove weather snapshots older than 90 days |
| `send_campaign` | On demand | Process and send a marketing campaign |
| `generate_monthly_invoices` | Monthly | Auto-generate rent invoices for active leases |
| `evaluate_all_streak_rewards` | Monthly (2nd) | Evaluate on-time payment streaks, grant tier rewards |
| `auto_apply_rewards_to_invoices` | Daily | Apply reward balances to outstanding invoices (where enabled) |

**Daily task chain order:** `generate_monthly_invoices` → `apply_late_fees` → `auto_apply_prepayment_credits` → `auto_apply_rewards_to_invoices` → `evaluate_all_streak_rewards` (monthly only)

Start the worker: `python manage.py qcluster`
