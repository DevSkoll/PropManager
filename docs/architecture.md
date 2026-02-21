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

PropManager is a Django monolith with 12 apps, each owning a specific domain. The application serves three distinct user types through separate portals.

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
                    │  │        12 Django Apps              │  │
                    │  │  accounts · properties · leases    │  │
                    │  │  billing · workorders · comms      │  │
                    │  │  documents · weather · marketing   │  │
                    │  │  tenant_lifecycle · rewards        │  │
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

45 models across 11 apps. All models use UUID primary keys via the `TimeStampedModel` abstract base.

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

### Billing (`apps/billing`) - 10 models

```
PaymentGatewayConfig
├── provider: stripe | paypal | square | authorize_net | braintree | plaid_ach | bitcoin
├── is_active, is_default
├── config: JSON (API keys, provider-specific settings)
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

WebhookEvent
├── provider, event_type, event_id, payload (JSON)
├── status: received | processed | failed | ignored
├── payment (nullable FK), error_message, ip_address

BitcoinWalletConfig (1:1 → PaymentGatewayConfig)
├── xpub, derivation_path, next_index, network

BitcoinPayment
├── invoice, btc_address (unique), derivation_index
├── status: pending | mempool | confirmed | expired | overpaid | underpaid
├── usd_amount, btc_usd_rate, expected_satoshis, received_satoshis
├── confirmations, txid, expires_at, confirmed_at
└── payment (1:1 → Payment, nullable)

BitcoinPriceSnapshot
├── btc_usd_rate, source
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
| `check_pending_btc_payments` | Every 2 minutes | Monitor pending Bitcoin payments via mempool.space |

**Daily task chain order:** `generate_monthly_invoices` → `apply_late_fees` → `auto_apply_prepayment_credits` → `auto_apply_rewards_to_invoices` → `evaluate_all_streak_rewards` (monthly only)

Start the worker: `python manage.py qcluster`

---

## Tenant Lifecycle (`apps/tenant_lifecycle`)

The tenant lifecycle app handles the complete onboarding process for new tenants.

### Data Model - 8 models

```
OnboardingTemplate (per property)
├── name, property, is_active, is_default
├── steps_config: JSON (enabled steps, order, requirements)
├── welcome_message, property_rules: Text
├── invitation_email_subject/body, sms_body
├── link_expiry_days: Integer (default 14)
├──→ OnboardingTemplateDocument (1:N) - required documents
└──→ OnboardingTemplateFee (1:N) - required fees/deposits

OnboardingSession
├── template, unit, lease (nullable), tenant (created during)
├── prospective_email, phone, first_name, last_name
├── status: invited | started | completed | expired | cancelled
├── current_step, steps_completed (JSON)
├── access_token: unique 48-char token
├── token_expires_at, invitation_sent_at, completed_at
├──→ OnboardingStepLog (1:N) - audit trail per step
├──→ OnboardingPayment (1:N) - payment tracking
└──→ OnboardingDocument (1:N) - document tracking

TenantVehicle
├── tenant, lease, onboarding_session
├── vehicle_type, make, model, year, color
├── license_plate, state, parking_space

TenantEmployment
├── tenant, lease
├── employment_type, employer_name, job_title
├── gross_income, income_frequency

TenantInsurance
├── tenant, lease
├── provider_name, policy_number, coverage_amount
├── start_date, end_date, policy_document
```

### Onboarding Steps

| Step | Description | Default |
|------|-------------|---------|
| Account Creation | OTP verification + account setup | Required |
| Personal Info | Name, DOB, phone, contact preference | Required |
| Emergency Contacts | Primary + secondary contacts | Required |
| Occupants | Additional household members | Optional |
| Pets | Pet registration with details | Optional |
| Vehicles | Vehicle registration for parking | Optional |
| Employment | Income/employer verification | Optional |
| Insurance | Renter's insurance policy | Optional |
| Documents | eSigning leases and agreements | Required |
| Payments | Deposits, fees, first month rent | Required |
| Welcome | Property info, rules, move-in checklist | Required |

### Onboarding Presets

15 pre-configured templates for common scenarios:

**Standard Templates:**
- Standard Residential
- Pet-Friendly Property
- Luxury/High-End
- Senior Living (55+)
- Student Housing
- Low-Income/Section 8

**Specialized Templates:**
- Corporate Relocation
- Military Housing (PCS/BAH)
- Roommate/Shared Living
- Lease Renewal (Existing Tenant)
- Month-to-Month Conversion
- Vacation/Short-Term Rental
- Affordable Housing (LIHTC)
- Emergency/Rapid Housing
- Furnished Corporate

---

## eDocuments (`apps/documents`)

Template-based electronic document system with markdown rendering and e-signatures.

### Data Model

```
EDocumentTemplate
├── name, template_type, description
├── content: Markdown with {{variables}} and [SIGNATURE:Role] tags
├── property (nullable - null = global)
├── is_active

EDocument
├── title, content (frozen markdown)
├── template (nullable - source template)
├── property, lease (nullable associations)
├── status: draft | pending | partial | completed | cancelled
├──→ EDocumentSigner (1:N) - signers
└──→ EDocumentSignature (1:N) - collected signatures

EDocumentSigner
├── document, user (nullable), email, role
├── signing_order, signing_token, token_expires_at
├── viewed_at, signed_at

EDocumentSignature
├── signer, signature_image (base64), typed_name
├── signed_at, ip_address
```

### Template Variables

Templates support variable substitution:

| Variable | Description |
|----------|-------------|
| `{{tenant_name}}` | Tenant's full name |
| `{{tenant_email}}` | Tenant's email |
| `{{property_name}}` | Property name |
| `{{property_address}}` | Full property address |
| `{{unit_number}}` | Unit identifier |
| `{{monthly_rent}}` | Lease rent amount |
| `{{security_deposit}}` | Security deposit |
| `{{lease_start_date}}` | Lease start date |
| `{{lease_end_date}}` | Lease end date |
| `{{today}}` | Current date |

### Signature Tags

```markdown
[SIGNATURE:Tenant]
[SIGNATURE:Landlord]
[SIGNATURE:Cosigner]
[SIGNATURE:Witness]
```

---

## Admin Navigation System

AWS-style app launcher with global search across all entities.

### Components

```
┌──────────────────────────────────────────────────────────┐
│ [≡]  PropManager     [Search apps, tenants...]  [🕐][👤] │
└──────────────────────────────────────────────────────────┘
  ↓                            ↓                     ↓
Launcher Modal          Global Search          User Menu
  - Pinned Apps          - Apps (instant)      - Settings
  - Recent Apps          - Tenants             - Logout
  - Categories           - Properties
    ├─ Dashboard         - Units
    ├─ Properties        - Leases
    ├─ Tenants           - Documents
    ├─ Leases            - Work Orders
    ├─ Billing           - Invoices
    ├─ Maintenance
    ├─ Communications
    ├─ Documents
    └─ Settings
```

### App Tiles

36 app tiles organized into 10 categories with:
- Gradient icons
- Badge counts (notifications, action items)
- Search keywords
- Pin/recent tracking via localStorage

### Global Search Architecture

**Hybrid Search:**
- Client-side: App tiles (instant, 50ms)
- Server-side: Database entities (debounced, 250ms)

**API Endpoint:** `GET /admin-portal/api/search/?q=<query>`

**Priority Order:**
1. Apps
2. Tenants
3. Properties
4. Units
5. Leases
6. Documents
7. Work Orders
8. Invoices

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + K` | Focus global search |
| `Ctrl/Cmd + /` | Open app launcher |
| `↓` / `↑` | Navigate search results |
| `Enter` | Select result |
| `Escape` | Close search/launcher |

### Context Processor

`apps.core.context_processors.app_launcher_context` provides:
- `app_tiles_json`: Serialized app tiles with resolved URLs
- `category_info_json`: Category metadata for display

Only loaded for authenticated admin users to minimize overhead.
