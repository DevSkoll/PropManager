# PropManager

**Property management software built by a landlord, for landlords — tenant-first, no compromises.**

I built PropManager because I needed it. Every tool on the market is either bloated enterprise software priced at $500/month or some half-baked spreadsheet replacement that falls apart the second you have more than three tenants. I knew there had to be something better — so I made it.

This is a full-stack Django application designed from the ground up for independent landlords and small property managers who want real, powerful software without the enterprise price tag or the enterprise headaches.

## About Me

I'm Skoll — an active duty service member running 8+ units on my own. My goal has always been to build the best tenant-landlord relationship possible, and that starts with building the best tools that put tenants first.

PropManager is one of those tools. I decided to release it under AGPL to share with the ADPI community and fellow service members who are also running their own units and building wealth through real estate. Within the demands of military life — deployments, TDYs, training rotations — PropManager makes it easy and fast to manage tenants, coordinate contractors, and handle every aspect of running properties from anywhere in the world.

I'm proud of what this platform has become. It's not a toy project — it's a powerful, production-ready system that I use myself every day. I genuinely believe PropManager holds the key to pleased tenants, proactive management, easier operations, and an open platform that the whole community can contribute to and make even better.

Every feature here reflects something I actually needed: passwordless login because my tenants shouldn't have to remember another password, seven pluggable payment gateways because nobody should be locked into one provider, Bitcoin payments because the future doesn't wait, weather alerts because my tenants deserve a heads-up before the storm hits, and a rewards program because great tenants deserve to be recognized.

If you have any questions, want to contribute, or just want to talk shop about real estate and tech, reach out to me at **x@skoll.dev**.

## Features

### Property & Tenant Management
- **Multi-Portal Architecture** — Dedicated portals for admins, tenants, and contractors, each with purpose-built UIs
- **First-Run Setup Wizard** — Guided configuration with auto-detection of existing data, database validation, and complete system setup
- **Passwordless Tenant Login** — Email/SMS OTP authentication so tenants never deal with passwords
- **Admin 2FA** — Optional two-factor authentication to keep admin accounts locked down
- **Tenant Management** — Complete tenant lifecycle with archive/restore, click-to-view detail modal, and safe deletion with blockers
- **Tenant Onboarding** — 15-step self-service wizard with email verification, insurance upload, ID verification, eDocument signing, and automated move-in invoicing
- **Onboarding Templates** — 15 pre-built templates (Standard, Premium, Luxury, Student, Military, etc.) with customizable steps and fee structures

### Lease & Document Management
- **Lease Management** — Complete lease lifecycle with electronic signatures, terms, occupants, pets, and month-to-month or fixed-term leases
- **eDocument System** — Markdown-based templates with signature blocks, auto-PDF generation, multi-party signing workflows, and lease auto-linking
- **Document Management** — Upload, categorize, and selectively share documents with tenants; automatic linking of onboarding documents (insurance, IDs, signed eDocuments)
- **Lease-Document Linking** — Associate documents and eDocuments with leases; upload directly from lease page or link existing documents

### Billing & Payments
- **Billing & Invoicing** — Automated invoice generation with late fees, interest, utility billing, recurring charges, and prepayment credits
- **7 Payment Gateways** — Stripe, PayPal, Square, Authorize.Net, Braintree, Plaid ACH, and Bitcoin — all configurable from the admin UI with guided setup forms, webhook signature verification, and connection testing
- **Bitcoin Payments** — Accept BTC with a locally managed HD wallet, real-time USD conversion via CoinGecko, mempool.space monitoring, and admin transfer controls
- **Tenant Rewards Program** — On-time payment streaks and prepayment bonuses to incentivize great tenants (legally distinct from credits — these are promotional, not real money)

### Maintenance & Communications
- **Work Order Management** — Full lifecycle from tenant submission through contractor completion with photo uploads, internal notes, and status tracking
- **Contractor Token Access** — Secure, expiring links for contractors with zero account setup required
- **Communications** — Threaded messaging, push notifications, SMS, and property-wide announcements
- **Weather Monitoring** — OpenWeatherMap integration with configurable thresholds and automatic tenant alerts for snow, wind, and extreme temperatures
- **Marketing Campaigns** — Email campaigns with tenant segmentation, scheduling, open/click tracking, and analytics
- **Reports & CSV Export** — Rent roll, aging receivables, payment history, and work order summaries

### AI & Automation
- **AI Provider Integration** — OpenAI, Anthropic Claude, and Google Gemini support for automated document generation and tenant communication
- **Automated Workflows** — Weather-based notifications, payment reminders, late fee application, and reward distribution
- **Background Task Queue** — Django-Q2 powered asynchronous processing for emails, invoices, and external API calls

## Tech Stack

| Component | Technology |
|---|---|
| Framework | Django 5.x |
| Database | PostgreSQL (production), SQLite (development) |
| Task Queue | Django-Q2 (ORM-backed or Redis) |
| Frontend | Django Templates + HTMX + Bootstrap 5 |
| Forms | django-crispy-forms + crispy-bootstrap5 |
| SMS | Twilio |
| Payments | Stripe, PayPal, Square, Authorize.Net, Braintree, Plaid ACH, Bitcoin |
| Bitcoin | bitcoinlib (HD wallet) + CoinGecko (pricing) + mempool.space (monitoring) |
| Weather | OpenWeatherMap API |
| Static Files | WhiteNoise |
| Deployment | Docker, Gunicorn, Nginx |

## Quick Start

**Choose your deployment method:**
- [Local Development](#local-development-sqlite) - Fastest for dev (SQLite + Python virtual env)
- [Docker Development](#docker-development) - Full stack (PostgreSQL + Redis + Worker)
- [Docker Production](#docker-production) - Production deployment with nginx

### Local Development (SQLite)

**Prerequisites:**
- Python 3.10+
- pip
- libgmp-dev (for Bitcoin wallet support: `sudo apt install libgmp-dev`)

**Setup:**

```bash
# 1. Clone and create virtual environment
git clone <repository> && cd PropManager
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/base.txt

# 2. Configure environment
cp .env.example .env
# Edit .env if needed (defaults work for dev)

# 3. Initialize database
python manage.py migrate

# 4. Seed demo data
python manage.py seed_dev_data

# 5. Start server
python manage.py runserver 0.0.0.0:8000
```

Visit `http://localhost:8000` to access the setup wizard.

**When to use:** Quick local development, testing, or when you don't need full services (PostgreSQL, Redis, background tasks).

### Docker Development

**Prerequisites:**
- Docker 20.10+
- Docker Compose 2.0+

**Setup:**

```bash
# 1. Clone repository
git clone <repository> && cd PropManager

# 2. Configure environment
cp .env.docker.example .env.docker
# Edit .env.docker if needed

# 3. Start all services
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# 4. Initialize database (in another terminal)
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_dev_data
```

**Services started:**
- `db` - PostgreSQL 16 (port 5432)
- `redis` - Redis 7 (port 6379)
- `web` - Django development server (port 8000)
- `worker` - Django-Q2 task worker

Visit `http://localhost:8000` to access the application.

**When to use:** Full-stack local development, testing background tasks, testing with PostgreSQL/Redis, or mimicking production environment.

**Useful commands:**

```bash
# View logs
docker compose logs -f web
docker compose logs -f worker

# Run migrations
docker compose exec web python manage.py migrate

# Access Django shell
docker compose exec web python manage.py shell

# Restart services
docker compose restart web worker

# Stop all services
docker compose down

# Stop and remove volumes (fresh start)
docker compose down -v
```

### Docker Production

**Prerequisites:**
- Docker 20.10+
- Docker Compose 2.0+
- SSL certificates (for HTTPS)

**Setup:**

```bash
# 1. Clone repository
git clone <repository> /opt/PropManager && cd /opt/PropManager

# 2. Configure environment
cp .env.docker.example .env.docker
# CRITICAL: Edit .env.docker with production values:
#   - Set SITE_URL=https://yourdomain.com
#   - Set strong SECRET_KEY (generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
#   - Set ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
#   - Set DEBUG=False
#   - Set POSTGRES_PASSWORD to a strong password
#   - Configure payment gateways
#   - Set email SMTP settings

# 3. Place SSL certificates
# Put fullchain.pem and privkey.pem in docker/nginx/ssl/
# Or use Let's Encrypt (see docs/deployment.md)

# 4. Start production stack
docker compose -f docker-compose.yml -f docker-compose.nginx.yml up -d --build

# 5. Initialize database
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --no-input

# 6. Access setup wizard
# Visit https://yourdomain.com/setup/ to complete initial configuration
```

**Services started:**
- `db` - PostgreSQL 16 (internal only)
- `redis` - Redis 7 (internal only)
- `web` - Gunicorn WSGI server (internal, port 8000)
- `worker` - Django-Q2 task worker
- `nginx` - Reverse proxy with SSL (ports 80/443)

Visit `https://yourdomain.com` to access the application.

**When to use:** Production deployments, staging environments, or public-facing instances.

**Monitoring:**

```bash
# Check service status
docker compose ps

# View application logs
docker compose logs -f web

# View worker logs
docker compose logs -f worker

# View nginx logs
docker compose logs -f nginx

# Check Django-Q task queue
docker compose exec web python manage.py qinfo
```

**Updating:**

```bash
cd /opt/PropManager  # Or your deployment directory
git pull origin master
docker compose -f docker-compose.yml -f docker-compose.nginx.yml up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --no-input
```

## Default Accounts

After running `python manage.py seed_dev_data`, the following accounts are available:

### Admin Portal (`/admin-portal/login/`)

| Username | Password | Role | Description |
|---|---|---|---|
| `admin` | `admin123` | Admin | Full access, superuser |
| `staff` | `staff123` | Staff | Full admin portal access |

### Tenant Portal (`/tenant/login/`)

Tenants use passwordless OTP login. In development, the OTP code is always **`123456`** (configured via `DEV_OTP_CODE` in `config/settings/development.py`).

| Email | Name | Unit |
|---|---|---|
| `tenant1@example.com` | Jane Smith | Sunset Apts #101 |
| `tenant2@example.com` | Bob Johnson | Sunset Apts #102 |
| `tenant3@example.com` | Maria Garcia | Sunset Apts #103 |
| `tenant4@example.com` | David Williams | Sunset Apts #104 |
| `tenant5@example.com` | Sarah Brown | Sunset Apts #105 |

### Django Admin (`/django-admin/`)

| Username | Password |
|---|---|
| `admin` | `admin123` |

### Contractor Access

Contractor links are generated by admins when assigning work orders. No accounts needed — contractors access their assigned work orders via unique token URLs (e.g., `/contractor/<token>/`).

## Sample Data

The seed command creates:

- **3 properties**: Sunset Apartments (8 units), Maple Grove Townhomes (4 units), Oak Street House (1 unit)
- **5 active leases** across Sunset Apartments
- **10 invoices** (current month issued + last month paid)
- **5 work orders** in various statuses (created, verified, assigned, in_progress, completed)
- **2 announcements**, message threads, and notifications
- **6 document categories** (Lease Agreements, Inspections, Financial, etc.)
- **Pre-configured payment gateways** (test mode)
- **Sample eDocument templates** (lease agreements, addendums)

## Project Structure

```
PropManager/
├── config/                  # Django settings, URLs, WSGI
│   ├── settings/
│   │   ├── base.py          # Shared settings
│   │   ├── development.py   # Dev overrides (SQLite, DEBUG=True)
│   │   └── production.py    # Prod overrides (PostgreSQL, SSL)
│   ├── urls.py              # Root URL configuration
│   └── wsgi.py
├── apps/
│   ├── core/                # Abstract models, services, middleware
│   ├── accounts/            # Users, auth, OTP, profiles
│   ├── properties/          # Properties, units, amenities
│   ├── leases/              # Leases, terms, terminations
│   ├── billing/             # Invoices, payments, gateways, Bitcoin
│   ├── rewards/             # Tenant rewards program
│   ├── workorders/          # Work orders, contractor assignments
│   ├── communications/      # Messages, notifications, announcements
│   ├── documents/           # File uploads, eDocuments, templates
│   ├── tenant_lifecycle/    # Onboarding wizard, templates
│   ├── weather/             # Weather monitoring, alerts
│   ├── marketing/           # Email campaigns, tracking
│   ├── ai/                  # AI provider integrations
│   └── setup/               # First-run setup wizard
├── templates/               # Django templates (organized by app)
├── static/                  # CSS, JS, images
├── media/                   # User uploads (gitignored)
├── docker/                  # Docker configuration files
│   ├── entrypoint.sh
│   └── nginx/
├── requirements/            # Python dependencies
│   ├── base.txt             # Core dependencies
│   ├── dev.txt              # Development tools
│   └── prod.txt             # Production dependencies
├── docs/                    # Documentation
├── Dockerfile               # Container image definition
├── docker-compose.yml       # Base services (db, redis, web, worker)
├── docker-compose.dev.yml   # Development overrides
├── docker-compose.nginx.yml # Production with nginx
├── WARP.md                  # AI/Developer context file
├── CHANGELOG.md             # Version history
└── README.md                # This file
```

## URL Structure

| Portal | Base URL | Login URL |
|---|---|---|
| Tenant | `/tenant/` | `/tenant/login/` |
| Admin | `/admin-portal/` | `/admin-portal/login/` |
| Contractor | `/contractor/<token>/` | N/A (token-based) |
| Setup Wizard | `/setup/` | N/A (redirects until complete) |
| Django Admin | `/django-admin/` | `/django-admin/` |

## Documentation

See the [`docs/`](docs/) directory for detailed documentation:

### Quick Links
- **[WARP.md](WARP.md)** — AI/Developer context file (start here!)
- [Documentation Index](docs/index.md) — Complete documentation hub
- [Deployment Guide](docs/deployment.md) — Production setup, Nginx, SSL, systemd

### User Guides
- [Admin Portal Guide](docs/guides/admin-guide.md) — Complete admin features walkthrough
- [Tenant Portal Guide](docs/guides/tenant-guide.md) — Tenant features and self-service
- [Contractor Guide](docs/guides/contractor-guide.md) — Token-based work order access
- [Onboarding Guide](docs/guides/onboarding-guide.md) — Tenant onboarding workflow

### Technical Documentation
- [Architecture Overview](docs/architecture.md) — System design, 45+ models across 14 apps
- [API & Services](docs/services.md) — Payment gateways, Bitcoin, SMS, email, weather
- [API Reference](docs/reference/api.md) — URL endpoints and views
- [Management Commands](docs/reference/commands.md) — Custom Django commands

### Development
- [Contributing](CONTRIBUTING.md) — How to contribute to PropManager
- [Development Workflow](docs/development/workflow.md) — Git branching, commits, PRs
- [Background Tasks](docs/development/tasks.md) — Django-Q2 task queue guide
- [Troubleshooting](docs/troubleshooting.md) — Common issues and solutions

### Other
- [Changelog](CHANGELOG.md) — Version history and release notes
- [Security Policy](SECURITY.md) — Vulnerability reporting and security features

## Configuration

All configuration is via environment variables (`.env` file or `.env.docker` for Docker). Key settings:

### Required (Production)

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | Django secret key | Generate with Python command |
| `DEBUG` | Debug mode | `False` (production) |
| `ALLOWED_HOSTS` | Comma-separated hostnames | `yourdomain.com,www.yourdomain.com` |
| `DATABASE_URL` | PostgreSQL connection string | `postgres://user:pass@host:5432/db` |
| `SITE_URL` | Base URL for emails/links | `https://propmanager.arctek.us` |

### Optional Features

| Variable | Description | Required For |
|---|---|---|
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | SMS features |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | SMS features |
| `TWILIO_PHONE_NUMBER` | Twilio sender number | SMS features |
| `OPENWEATHERMAP_API_KEY` | Weather API key | Weather features |
| `STRIPE_SECRET_KEY` | Stripe API key | Stripe payments |
| `PAYPAL_CLIENT_ID` | PayPal client ID | PayPal payments |
| `SQUARE_ACCESS_TOKEN` | Square access token | Square payments |
| `BITCOIN_ENCRYPTION_KEY` | AES-256 key for hot wallet | Bitcoin payments |
| `REDIS_URL` | Redis connection string | Redis cache/queue |
| `OPENAI_API_KEY` | OpenAI API key | AI features |
| `ANTHROPIC_API_KEY` | Anthropic API key | AI features |

See [`.env.example`](.env.example) or [`.env.docker.example`](.env.docker.example) for the complete list.

## Management Commands

| Command | Description |
|---|---|
| `python manage.py seed_dev_data` | Create dev accounts and sample data |
| `python manage.py seed_dev_data --reset` | Flush DB and reseed everything |
| `python manage.py createsuperuser` | Create a new admin user manually |
| `python manage.py migrate` | Run database migrations |
| `python manage.py collectstatic` | Collect static files (production) |
| `python manage.py qcluster` | Start background task worker |
| `python manage.py qinfo` | View Django-Q task queue status |
| `python manage.py check --deploy` | Validate production settings |

## Background Tasks (Django-Q2)

Start the task worker for background processing:

```bash
# Local development
python manage.py qcluster

# Docker
# Worker starts automatically in docker-compose
```

Tasks include:
- Invoice generation, late fee application, and overdue detection
- Prepayment credit and reward auto-application
- Streak reward evaluation (monthly)
- OTP delivery (email/SMS)
- Weather polling and alert generation
- Bitcoin payment monitoring (every 2 minutes via mempool.space)
- Marketing campaign sending
- Notification dispatch
- eDocument PDF generation

## License

PropManager is dual-licensed:

### Open Source — AGPL-3.0

This project is licensed under the [GNU Affero General Public License v3.0](LICENSE). Under AGPL-3.0:

- You may use, modify, and distribute this software freely
- Any modifications or derivative works **must** be released under the same AGPL-3.0 license
- If you run a modified version as a network service (SaaS), you **must** make the complete source code available to users of that service
- All changes must be contributed back under the same terms

### Commercial / Proprietary License

If you wish to use PropManager in a proprietary or closed-source product — including SaaS offerings where you do not wish to release your source code — you must obtain a **commercial license** from the copyright holder. Commercial licenses include royalty terms.

For licensing inquiries, contact the project maintainer.

**Copyright (c) 2026 DevSkoll. All rights reserved.**
