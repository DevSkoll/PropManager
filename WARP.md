# PropManager - AI Context & Developer Orientation (WARP.md)

**Purpose:** This file provides comprehensive context for AI assistants (Claude, GPT, etc.) and human developers to quickly understand PropManager's architecture, conventions, and common operations.

**Last Updated:** 2026-02-21
**Version:** 1.0.0

---

## Table of Contents

1. [Project Identity](#project-identity)
2. [Quick Start](#quick-start)
3. [Architecture Overview](#architecture-overview)
4. [App Structure](#app-structure)
5. [Common Patterns](#common-patterns)
6. [Key File Locations](#key-file-locations)
7. [Database Schema](#database-schema)
8. [Authentication](#authentication)
9. [Background Tasks](#background-tasks)
10. [Docker Deployment](#docker-deployment)
11. [Common Operations](#common-operations)
12. [Troubleshooting Quick Reference](#troubleshooting-quick-reference)

---

## Project Identity

**Name:** PropManager
**Type:** Property Management SaaS
**Framework:** Django 5.x + HTMX + Bootstrap 5
**Language:** Python 3.10+
**Database:** PostgreSQL (prod), SQLite (dev)
**License:** AGPL-3.0 / Commercial Dual License

**Core Philosophy:**
- Tenant-first design
- No vendor lock-in (7 payment gateways)
- Real production system (in active use)
- Built by landlord for landlords
- ADPI/military community focused

---

## Quick Start

### Local Development (SQLite)

```bash
# Clone and setup
git clone <repo> && cd PropManager
python3 -m venv venv && source venv/bin/activate
pip install -r requirements/base.txt

# Configure
cp .env.example .env
# Edit .env - defaults work for dev

# Initialize
python manage.py migrate
python manage.py seed_dev_data  # Creates demo data

# Run
python manage.py runserver 0.0.0.0:8000
```

**Default Accounts:**
- Admin: `admin` / `admin123` → `/admin-portal/login/`
- Tenant: `tenant1@example.com` (OTP code: `123456` in dev)

### Docker Development

```bash
# Start all services (PostgreSQL + Redis + Web + Worker)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Run migrations
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_dev_data

# Access: http://localhost:8000
```

### Docker Production

```bash
# Use docker-compose.yml + docker-compose.nginx.yml
docker compose -f docker-compose.yml -f docker-compose.nginx.yml up -d
```

---

## Architecture Overview

### Three-Portal Architecture

```
PropManager
├── /tenant/*          → Tenant Portal (passwordless OTP)
├── /admin-portal/*    → Admin Portal (password + optional 2FA)
├── /contractor/*      → Contractor Portal (token-based, no account)
├── /setup/*           → First-Run Setup Wizard
└── /django-admin/     → Django Admin (superuser only)
```

### Request Flow

```
User Request
  ↓
NGINX (optional, prod only)
  ↓
Django (Gunicorn in prod, runserver in dev)
  ↓
Middleware Stack:
  1. SecurityMiddleware
  2. WhiteNoiseMiddleware
  3. SessionMiddleware
  4. AuthenticationMiddleware
  5. HtmxMiddleware
  6. SetupRequiredMiddleware  ← Redirects to /setup/ if incomplete
  7. RoleBasedAccessMiddleware ← Enforces /tenant/ vs /admin-portal/ access
  ↓
URL Routing → View → Template → Response
```

### 12 Django Apps

| App | Purpose | Models |
|-----|---------|--------|
| `core` | Abstract base classes, services, utilities | 1 |
| `accounts` | Users, auth, OTP, profiles, contractor tokens | 5 |
| `properties` | Properties, units, amenities | 4 |
| `leases` | Leases, terms, terminations | 3 |
| `billing` | Invoices, payments, 7 gateways, Bitcoin | 10 |
| `rewards` | Streak & prepayment reward system | 6 |
| `workorders` | Maintenance requests, contractor assignments | 4 |
| `communications` | Messages, notifications, announcements | 4 |
| `documents` | File uploads, eDocuments, templates | 6 |
| `tenant_lifecycle` | Onboarding wizard, templates | 8 |
| `weather` | Weather monitoring & alerts | 3 |
| `marketing` | Email campaigns & tracking | 4 |
| `ai` | AI provider integrations | 2 |
| `setup` | First-run setup wizard | 2 |

**Total:** 45+ models

---

## App Structure

### Standard App Layout

```
apps/<app_name>/
├── __init__.py
├── apps.py                  # AppConfig
├── models.py                # Data models
├── views.py                 # Main views
├── urls_admin.py            # Admin portal URLs (optional)
├── urls_tenant.py           # Tenant portal URLs (optional)
├── forms.py                 # Django forms
├── services/                # Business logic (optional)
│   ├── __init__.py
│   └── service_name.py
├── tasks.py                 # Django-Q2 background tasks (optional)
├── admin.py                 # Django admin registration
├── migrations/
└── tests.py
```

### URL Namespaces

```python
# URLs are namespaced by portal:
accounts_admin      → apps/accounts/urls_admin.py
accounts_tenant     → apps/accounts/urls_tenant.py
billing_admin       → apps/billing/urls_admin.py
billing_tenant      → apps/billing/urls_tenant.py
# etc.
```

**Reverse URL Example:**
```python
from django.urls import reverse
reverse('accounts_admin:admin_dashboard')  # /admin-portal/
reverse('billing_tenant:invoice_list')     # /tenant/invoices/
```

---

## Common Patterns

### 1. TimeStampedModel Base Class

**Location:** `apps/core/models.py`

```python
from apps.core.models import TimeStampedModel

class MyModel(TimeStampedModel):
    # Automatically includes:
    # - id (UUID, primary key)
    # - created_at (auto, indexed)
    # - updated_at (auto)
    name = models.CharField(max_length=200)
```

### 2. AuditMixin for Change Tracking

```python
from apps.core.models import TimeStampedModel, AuditMixin

class Invoice(TimeStampedModel, AuditMixin):
    # Adds:
    # - created_by (FK → User, nullable)
    # - updated_by (FK → User, nullable)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
```

### 3. View Decorators

```python
from apps.core.decorators import tenant_required, admin_required

@tenant_required
def tenant_dashboard(request):
    # Ensures user.role == 'tenant'
    pass

@admin_required
def admin_dashboard(request):
    # Ensures user.role in ('admin', 'staff')
    pass
```

### 4. URL Generation

**For emails/external links:** Use `get_absolute_url()` from `apps/core/url_utils.py`

```python
from apps.core.url_utils import get_absolute_url

# With path
url = get_absolute_url('/tenant/dashboard/')
# → https://propmanager.arctek.us/tenant/dashboard/

# With view name
url = get_absolute_url('leases_signing:signing_page', token='abc123')
# → https://propmanager.arctek.us/lease/sign/abc123/
```

**Configuration:** Set `SITE_URL` in `.env`

### 5. Background Tasks (Django-Q2)

```python
# apps/billing/tasks.py
from django_q.tasks import async_task

def generate_monthly_invoices():
    """Monthly invoice generation."""
    # Task logic here
    pass

# Schedule from view or task
async_task('apps.billing.tasks.generate_monthly_invoices')
```

### 6. Services Pattern

Business logic lives in `services/` subdirectories:

```python
# apps/billing/services/payment_service.py
class PaymentService:
    def __init__(self, gateway_provider):
        self.provider = gateway_provider

    def process_payment(self, invoice, amount, payment_method_token):
        # Payment processing logic
        pass
```

---

## Key File Locations

### Configuration

| File | Purpose |
|------|---------|
| `config/settings/base.py` | Shared settings (all environments) |
| `config/settings/development.py` | Dev overrides (SQLite, DEBUG=True) |
| `config/settings/production.py` | Prod overrides (PostgreSQL, SSL, HSTS) |
| `config/urls.py` | Root URL configuration |
| `.env` | Environment variables (git ignored) |
| `.env.example` | Environment template (dev defaults) |
| `.env.docker.example` | Docker environment template |

### Docker

| File | Purpose |
|------|---------|
| `Dockerfile` | Web/worker container image |
| `docker-compose.yml` | Base services (db, redis, web, worker) |
| `docker-compose.dev.yml` | Dev overrides (DEBUG=True, ports) |
| `docker-compose.nginx.yml` | Production with nginx reverse proxy |
| `docker/entrypoint.sh` | Container startup script |
| `docker/nginx/nginx.conf` | Nginx configuration |

### Templates

```
templates/
├── base.html                    # Global base template
├── admin_portal/                # Admin portal templates
│   ├── base_admin.html
│   └── dashboard.html
├── tenant/                      # Tenant portal templates
│   ├── base_tenant.html
│   └── dashboard.html
├── setup/                       # Setup wizard
│   ├── base_wizard.html
│   └── step_*.html
├── leases/                      # Lease management
├── billing/                     # Billing & payments
└── [app_name]/                  # Per-app templates
```

### Static Files

```
static/
├── css/
│   └── custom.css               # Global custom styles
├── js/
│   └── app-launcher.js          # AWS-style nav
└── images/
```

### Management Commands

| Command | File Location |
|---------|---------------|
| `seed_dev_data` | `apps/core/management/commands/seed_dev_data.py` |
| `qcluster` | Django-Q2 (installed package) |
| `migrate` | Django core |
| `createsuperuser` | Django core |

---

## Database Schema

### User Model

**Location:** `apps/accounts/models.py`

```python
User (extends AbstractUser)
├── id: UUID
├── username: str (unique)
├── email: str (unique, indexed)
├── role: 'tenant' | 'admin' | 'staff'
├── phone_number: str
├── is_phone_verified: bool
├── is_email_verified: bool
├── preferred_contact: 'email' | 'sms' | 'both'
├── is_archived: bool (soft delete for tenants)
└── Relationships:
    ├── tenant_profile (1:1 → TenantProfile)
    ├── admin_profile (1:1 → AdminProfile)
    └── otp_tokens (1:N → OTPToken)
```

### Key Relationships

```python
Property (1:N) → Unit
Unit (1:1) → Lease (active)
Lease (N:1) → User (tenant)
Lease (1:N) → Invoice
Invoice (1:N) → Payment
Invoice (1:N) → InvoiceLineItem
User (1:1) → RewardBalance
RewardBalance (1:N) → RewardTransaction
WorkOrder (N:1) → Unit
WorkOrder (1:N) → ContractorAccessToken
```

### Singleton Models (pk=1)

- `SetupConfiguration` - First-run setup state
- `BitcoinWalletConfig` - Bitcoin wallet config

### UUID Primary Keys

All models inherit from `TimeStampedModel` which uses UUID primary keys:

```python
id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
```

**Benefits:**
- No sequential ID enumeration attacks
- Distributed system friendly
- Merge-safe across environments

---

## Authentication

### Tenant: Passwordless OTP

**Flow:**
1. Tenant enters email or phone
2. System generates 6-digit OTP (10 min expiry)
3. OTP sent via email/SMS
4. Tenant enters code
5. System validates → Django session created

**Development:** OTP is always `123456` (set via `DEV_OTP_CODE` in `development.py`)

**Implementation:**
- Backend: `apps/accounts/backends.PasswordlessOTPBackend`
- Rate limit: 5 requests/hour per user
- View: `apps/accounts/views.tenant_otp_login_request`

### Admin: Password + Optional 2FA

**Flow:**
1. Username + password (Django ModelBackend)
2. If `AdminProfile.otp_enabled = True`:
   - Generate OTP
   - Send via configured method (email/SMS)
   - Validate second factor
3. Create session

**Enable 2FA:** Admin settings page or Django admin

### Contractor: Token-Based

**Flow:**
1. Admin assigns contractor to work order
2. System generates `ContractorAccessToken` (48-byte URL-safe)
3. Contractor accesses `/contractor/<token>/`
4. Token validated (not expired/revoked)
5. Scoped access to assigned work order only

**No Django session** - token attached to request via decorator

---

## Background Tasks

### Django-Q2 Configuration

**Broker:** ORM-backed (default) or Redis (if `REDIS_URL` set)

**Worker Start:**
```bash
python manage.py qcluster
```

**Docker:** Worker runs automatically in `propmanager-worker` service

### Scheduled Tasks

| Task | Schedule | Function |
|------|----------|----------|
| Invoice generation | Monthly (1st, 1am) | `generate_monthly_invoices` |
| Late fees | Daily (1am) | `apply_late_fees` |
| Overdue checks | Daily (2am) | `check_overdue_invoices` |
| Prepayment credits | Daily (12:30am) | `auto_apply_prepayment_credits` |
| Reward application | Daily (1:30am) | `auto_apply_rewards_to_invoices` |
| Streak evaluation | Monthly (2nd, 2am) | `evaluate_all_streak_rewards` |
| Weather polling | Every 2 hours | `poll_weather_for_all_properties` |
| Bitcoin monitoring | Every 2 minutes | `check_pending_btc_payments` |
| Campaign processing | Every 5 minutes | `process_scheduled_campaigns` |

### Task Definition Example

```python
# apps/billing/tasks.py
def generate_monthly_invoices():
    """Generate invoices for active leases on the 1st of each month."""
    from apps.leases.models import Lease
    from apps.billing.models import Invoice

    active_leases = Lease.objects.filter(status='active')
    for lease in active_leases:
        Invoice.objects.create(
            lease=lease,
            tenant=lease.tenant,
            # ...
        )
```

---

## Docker Deployment

### Development Mode

**File:** `docker-compose.dev.yml`

```bash
# Start services
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Services:
# - db (PostgreSQL)
# - redis
# - web (Django runserver, port 8000)
# - worker (Django-Q2)
```

**Features:**
- DEBUG=True
- SQLite or PostgreSQL (configured via `DATABASE_URL`)
- Auto-reload on code changes
- Console email backend

**Access:**
- Web: http://localhost:8000
- Django Admin: http://localhost:8000/django-admin/
- PostgreSQL: localhost:5432

### Production Mode

**File:** `docker-compose.nginx.yml`

```bash
# Start with nginx reverse proxy
docker compose -f docker-compose.yml -f docker-compose.nginx.yml up -d

# Services:
# - db (PostgreSQL)
# - redis
# - web (Gunicorn, internal only)
# - worker (Django-Q2)
# - nginx (port 80/443)
```

**Features:**
- DEBUG=False
- HTTPS with SSL certificates
- Static file serving via nginx
- Gunicorn WSGI server
- Production security headers

**Configuration:**
1. Copy `.env.docker.example` to `.env.docker`
2. Set `SITE_URL=https://yourdomain.com`
3. Set `ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com`
4. Configure payment gateway keys
5. Set strong `SECRET_KEY`

**SSL Certificates:**
Place in `docker/nginx/ssl/`:
- `fullchain.pem` (certificate + chain)
- `privkey.pem` (private key)

### Docker Secrets (Swarm/Production)

Set sensitive values as Docker secrets:

```bash
# Create secrets
echo "your-secret-key" | docker secret create django_secret_key -
echo "your-db-password" | docker secret create postgres_password -

# Mount at /run/secrets/<secret_name>
# Django reads via get_secret() in settings/base.py
```

### Common Docker Commands

```bash
# View logs
docker compose logs -f web
docker compose logs -f worker

# Run migrations
docker compose exec web python manage.py migrate

# Access shell
docker compose exec web python manage.py shell

# Seed data
docker compose exec web python manage.py seed_dev_data

# Restart services
docker compose restart web worker

# Stop all
docker compose down

# Rebuild after code changes
docker compose up --build -d
```

---

## Common Operations

### 1. Add a New Django App

```bash
# Create app structure
mkdir -p apps/newapp
cd apps/newapp
django-admin startapp newapp .

# Add to INSTALLED_APPS
# config/settings/base.py:
INSTALLED_APPS = [
    ...
    'apps.newapp',
]

# Create URLs
touch urls_admin.py urls_tenant.py

# Register in main URLs
# config/urls.py:
path('admin-portal/', include('apps.newapp.urls_admin')),
path('tenant/', include('apps.newapp.urls_tenant')),
```

### 2. Add a Background Task

```python
# 1. Create task function
# apps/billing/tasks.py
def my_background_task():
    # Task logic
    pass

# 2. Schedule from view/management command
from django_q.tasks import async_task
async_task('apps.billing.tasks.my_background_task')

# 3. Or schedule recurring (Django admin → Django-Q → Schedules)
```

### 3. Add a Payment Gateway

```python
# 1. Add config to PaymentGatewayConfig.PROVIDER_CHOICES
# apps/billing/models.py

# 2. Create form in apps/billing/forms.py
class NewGatewayForm(forms.Form):
    api_key = forms.CharField()
    # ...

# 3. Add to PROVIDER_FORM_MAP
PROVIDER_FORM_MAP = {
    ...
    'new_gateway': NewGatewayForm,
}

# 4. Implement in PaymentService
# apps/billing/services/payment_service.py
```

### 4. Modify Setup Wizard Steps

**Location:** `apps/setup/models.py`

```python
WIZARD_STEPS = [
    {
        "key": "new_step",
        "title": "New Step",
        "description": "Description",
        "icon": "bi-icon-name",
        "required": True,
    },
    # ...
]
```

**Add view:** `apps/setup/views.py`
**Add template:** `templates/setup/step_new_step.html`
**Add URL:** `apps/setup/urls.py`

### 5. Add to Global Search

**Location:** `apps/core/views_api.py` → `global_search()`

```python
# Add new entity type
if entity_type == 'new_entity':
    results.extend([
        {
            'type': 'New Entity',
            'title': obj.name,
            'subtitle': obj.description,
            'url': reverse('app:detail', args=[obj.pk]),
        }
        for obj in NewModel.objects.filter(name__icontains=query)[:5]
    ])
```

### 6. Deploy New Version

```bash
# Traditional (systemd)
cd /opt/propmanager
git pull origin main
source venv/bin/activate
pip install -r requirements/base.txt
python manage.py migrate
python manage.py collectstatic --no-input
sudo systemctl restart propmanager propmanager-worker

# Docker
cd /opt/propmanager
git pull origin main
docker compose -f docker-compose.yml -f docker-compose.nginx.yml up -d --build
docker compose exec web python manage.py migrate
```

---

## Troubleshooting Quick Reference

### Issue: Setup wizard redirects everywhere

**Cause:** `SetupConfiguration.is_complete = False`

**Fix:**
```python
from apps.setup.models import SetupConfiguration
config = SetupConfiguration.get_instance()
config.is_complete = True
config.save()
```

### Issue: OTP code not working (dev)

**Cause:** Dev OTP code is `123456` hardcoded

**Check:** `config/settings/development.py` → `DEV_OTP_CODE`

### Issue: Static files not loading

**Fix:**
```bash
python manage.py collectstatic --no-input
```

### Issue: Docker services won't start

**Check:**
```bash
docker compose logs web
docker compose logs db
```

**Common:** Database not ready. Wait 5 seconds and retry.

### Issue: Payment gateway not working

**Check:**
1. Environment variables set (`.env`)
2. `PaymentGatewayConfig` exists and `is_active=True`
3. Webhook URL configured with provider
4. Check logs: `docker compose logs web`

### Issue: Background tasks not running

**Check:**
1. Worker running: `docker compose ps worker` or `systemctl status propmanager-worker`
2. Django-Q dashboard: http://localhost:8000/admin-portal/django-q/
3. Worker logs: `docker compose logs worker`

### Issue: Email not sending

**Development:** Check console output (console backend)

**Production:**
1. Verify SMTP settings in `.env`
2. Check `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`
3. Test credentials: `python manage.py shell`
   ```python
   from django.core.mail import send_mail
   send_mail('Test', 'Body', 'from@example.com', ['to@example.com'])
   ```

### Issue: Container exits immediately

**Check:** `docker compose logs web`

**Common Causes:**
- Missing environment variables
- Database connection failed
- Syntax error in code

---

## Development Workflow

### Git Branching Strategy

- `master` - Production-ready code
- `develop` - Integration branch
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `hotfix/*` - Production hotfixes

### Code Style

- PEP 8 compliance
- Black formatter (optional)
- Import order: stdlib → third-party → local
- Docstrings for complex functions

### Testing

```bash
# Run tests
python manage.py test

# Run specific app
python manage.py test apps.billing

# With coverage
coverage run --source='apps' manage.py test
coverage report
```

---

## Environment Variables Quick Reference

### Required (Production)

| Variable | Example | Purpose |
|----------|---------|---------|
| `SECRET_KEY` | `django-insecure-...` | Django secret key |
| `ALLOWED_HOSTS` | `yourdomain.com,www.yourdomain.com` | Allowed hostnames |
| `DATABASE_URL` | `postgres://user:pass@host:5432/db` | PostgreSQL connection |
| `SITE_URL` | `https://propmanager.arctek.us` | Base URL for emails/links |

### Optional Features

| Variable | Purpose |
|----------|---------|
| `TWILIO_ACCOUNT_SID` | SMS OTP & notifications |
| `TWILIO_AUTH_TOKEN` | Twilio authentication |
| `STRIPE_SECRET_KEY` | Stripe payments |
| `PAYPAL_CLIENT_ID` | PayPal payments |
| `OPENWEATHERMAP_API_KEY` | Weather monitoring |
| `REDIS_URL` | Redis cache/queue |

See `.env.example` for complete list.

---

## File Naming Conventions

| Pattern | Purpose |
|---------|---------|
| `urls_admin.py` | Admin portal URLs |
| `urls_tenant.py` | Tenant portal URLs |
| `urls_signing.py` | Public/token-based URLs (leases) |
| `views_*.py` | Specialized view modules |
| `forms.py` | Django forms |
| `tasks.py` | Background tasks |
| `services/` | Business logic modules |
| `base_*.html` | Base templates |
| `step_*.html` | Wizard step templates |

---

## Performance Considerations

### Database

- All models have `created_at` indexed
- Use `select_related()` for foreign keys
- Use `prefetch_related()` for reverse FKs and M2M
- Avoid N+1 queries in templates

### Caching

- Redis for sessions (if `REDIS_URL` set)
- WhiteNoise for static files (30-day cache)
- Template fragment caching where needed

### Background Tasks

- Use async tasks for:
  - Email sending
  - Invoice generation
  - Payment processing
  - External API calls

---

## Security Features

### Enabled in Production

- `SECURE_SSL_REDIRECT = True`
- `SECURE_HSTS_SECONDS = 31536000` (1 year)
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- `X_FRAME_OPTIONS = 'DENY'`
- `SECURE_CONTENT_TYPE_NOSNIFF = True`
- `SECURE_BROWSER_XSS_FILTER = True`

### Additional

- UUID primary keys (no enumeration)
- Rate-limited OTP (5/hour)
- Webhook signature verification
- Password validation (Django validators)
- CSRF protection on all POST requests

---

## API Integration Points

### External APIs Used

| Service | Purpose | Config |
|---------|---------|--------|
| Twilio | SMS OTP, notifications | `TWILIO_*` env vars |
| Stripe | Credit card payments | `STRIPE_*` env vars |
| PayPal | PayPal payments | `PAYPAL_*` env vars |
| OpenWeatherMap | Weather data | `OPENWEATHERMAP_API_KEY` |
| mempool.space | Bitcoin monitoring | No auth (public API) |
| CoinGecko | BTC/USD pricing | No auth (free tier) |

### Webhooks (Inbound)

| Endpoint | Provider | Purpose |
|----------|----------|---------|
| `/tenant/billing/webhook/stripe/` | Stripe | Payment events |
| `/tenant/billing/webhook/paypal/` | PayPal | Payment events |
| `/tenant/billing/webhook/square/` | Square | Payment events |

**Security:** All webhooks verify signatures before processing.

---

## Contact & Support

**Maintainer:** Skoll (x@skoll.dev)
**Repository:** [GitHub](https://github.com/DevSkoll/PropManager)
**License:** AGPL-3.0 / Commercial
**Documentation:** `/docs/`

---

**End of WARP.md**

This file should be updated whenever significant architectural changes are made.
