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

- **Multi-Portal Architecture** — Dedicated portals for admins, tenants, and contractors, each with purpose-built UIs
- **Passwordless Tenant Login** — Email/SMS OTP authentication so tenants never deal with passwords
- **Admin 2FA** — Optional two-factor authentication to keep admin accounts locked down
- **Billing & Invoicing** — Automated invoice generation with late fees, interest, utility billing, recurring charges, and prepayment credits
- **7 Payment Gateways** — Stripe, PayPal, Square, Authorize.Net, Braintree, Plaid ACH, and Bitcoin — all configurable from the admin UI with guided setup forms, webhook signature verification, and connection testing
- **Bitcoin Payments** — Accept BTC with a locally managed HD wallet, real-time USD conversion via CoinGecko, mempool.space monitoring, and admin transfer controls
- **Tenant Rewards Program** — On-time payment streaks and prepayment bonuses to incentivize great tenants (legally distinct from credits — these are promotional, not real money)
- **Work Order Management** — Full lifecycle from tenant submission through contractor completion with photo uploads, internal notes, and status tracking
- **Contractor Token Access** — Secure, expiring links for contractors with zero account setup required
- **Communications** — Threaded messaging, push notifications, SMS, and property-wide announcements
- **Document Management** — Upload, categorize, and selectively share documents with tenants
- **Weather Monitoring** — OpenWeatherMap integration with configurable thresholds and automatic tenant alerts for snow, wind, and extreme temperatures
- **Marketing Campaigns** — Email campaigns with tenant segmentation, scheduling, open/click tracking, and analytics
- **Reports & CSV Export** — Rent roll, aging receivables, payment history, and work order summaries

## Tech Stack

| Component | Technology |
|---|---|
| Framework | Django 5.x |
| Database | PostgreSQL (production), SQLite (development) |
| Task Queue | Django-Q2 (ORM-backed) |
| Frontend | Django Templates + HTMX + Bootstrap 5 |
| Forms | django-crispy-forms + crispy-bootstrap5 |
| SMS | Twilio |
| Payments | Stripe, PayPal, Square, Authorize.Net, Braintree, Plaid ACH, Bitcoin |
| Bitcoin | bitcoinlib (HD wallet) + CoinGecko (pricing) + mempool.space (monitoring) |
| Weather | OpenWeatherMap API |
| Static Files | WhiteNoise |

## Quick Start

### Prerequisites

- Python 3.10+
- pip
- libgmp-dev (for Bitcoin wallet support: `sudo apt install libgmp-dev`)
- (Optional) PostgreSQL for production

### 1. Clone and set up the virtual environment

```bash
cd propmanager
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/base.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your settings (defaults work for development)
```

### 3. Run migrations

```bash
python manage.py migrate
```

### 4. Seed development data

```bash
python manage.py seed_dev_data
```

This creates default accounts, sample properties, leases, invoices, work orders, and more. See [Default Accounts](#default-accounts) below.

### 5. Start the development server

```bash
python manage.py runserver 0.0.0.0:8000
```

Visit `http://localhost:8000` to get started.

## Default Accounts

After running `python manage.py seed_dev_data`, the following accounts are available:

### Admin Portal (`/admin-portal/login/`)

| Username | Password | Role | Description |
|---|---|---|---|
| `admin` | `admin123` | Admin | Full access, superuser |
| `staff` | `staff123` | Staff | Full admin portal access |

### Tenant Portal (`/tenant/login/`)

Tenants use passwordless OTP login. In development, the OTP code is always **`123456`** (configured via `DEV_OTP_CODE` in `config/settings/development.py`).

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

Contractor links are generated by admins when assigning work orders. No accounts needed — contractors access their assigned work orders via unique token URLs (e.g., `/contractor/<token>/`).

## Sample Data

The seed command creates:

- **3 properties**: Sunset Apartments (8 units), Maple Grove Townhomes (4 units), Oak Street House (1 unit)
- **5 active leases** across Sunset Apartments
- **10 invoices** (current month issued + last month paid)
- **5 work orders** in various statuses (created, verified, assigned, in_progress, completed)
- **2 announcements**, message threads, and notifications
- **6 document categories** (Lease Agreements, Inspections, Financial, etc.)

## Project Structure

```
propmanager/
    config/              # Django settings (base/development/production), URLs
    apps/
        core/            # Abstract models, services, decorators, middleware, reports
        accounts/        # Users, auth, OTP, profiles, contractor tokens
        properties/      # Properties, units, amenities
        leases/          # Leases, terms, terminations
        billing/         # Invoices, payments, 7 payment gateways, Bitcoin wallet
        workorders/      # Work orders, contractor assignments, notes, images
        communications/  # Messages, notifications, announcements
        documents/       # File uploads, categories
        weather/         # Weather monitoring, alerts
        marketing/       # Email campaigns, segmentation, tracking
        rewards/         # Tenant rewards, streak tracking, prepayment bonuses
    templates/           # All HTML templates organized by app
    static/              # CSS, JS, images
    media/               # User uploads (gitignored)
    requirements/        # Dependency files (base/dev/prod)
    docs/                # Architecture, services, deployment guides
```

## URL Structure

| Portal | Base URL | Login URL |
|---|---|---|
| Tenant | `/tenant/` | `/tenant/login/` |
| Admin | `/admin-portal/` | `/admin-portal/login/` |
| Contractor | `/contractor/<token>/` | N/A (token-based) |
| Django Admin | `/django-admin/` | `/django-admin/` |

## Documentation

See the [`docs/`](docs/) directory for detailed documentation:

### Getting Started
- [Documentation Index](docs/index.md) — Complete documentation hub
- [Quick Start](docs/development/getting-started.md) — Local development setup
- [Deployment Guide](docs/deployment.md) — Production setup, Nginx, SSL, systemd

### User Guides
- [Admin Portal Guide](docs/guides/admin-guide.md) — Complete admin features walkthrough
- [Tenant Portal Guide](docs/guides/tenant-guide.md) — Tenant features and self-service
- [Contractor Guide](docs/guides/contractor-guide.md) — Token-based work order access

### Technical Documentation
- [Architecture Overview](docs/architecture.md) — System design, 45 models across 11 apps, authentication flows
- [API & Services](docs/services.md) — Payment gateways, Bitcoin wallet, SMS, email, weather, rewards
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

All configuration is via environment variables (`.env` file). Key settings:

| Variable | Description | Required |
|---|---|---|
| `SECRET_KEY` | Django secret key | Yes (production) |
| `DEBUG` | Debug mode | No (default: False) |
| `DATABASE_URL` | PostgreSQL connection string | Production only |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | For SMS features |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | For SMS features |
| `TWILIO_PHONE_NUMBER` | Twilio sender number | For SMS features |
| `OPENWEATHERMAP_API_KEY` | Weather API key | For weather features |
| `STRIPE_SECRET_KEY` | Stripe API key | For Stripe payments |
| `PAYPAL_CLIENT_ID` | PayPal client ID | For PayPal payments |
| `SQUARE_ACCESS_TOKEN` | Square access token | For Square payments |
| `BITCOIN_ENCRYPTION_KEY` | AES-256 key for hot wallet | For Bitcoin payments |

See [`.env.example`](.env.example) for the complete list, including Authorize.Net, Braintree, and Plaid credentials.

## Management Commands

| Command | Description |
|---|---|
| `python manage.py seed_dev_data` | Create dev accounts and sample data |
| `python manage.py seed_dev_data --reset` | Flush DB and reseed everything |
| `python manage.py createsuperuser` | Create a new admin user manually |

## Background Tasks (Django-Q2)

Start the task worker for background processing:

```bash
python manage.py qcluster
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
