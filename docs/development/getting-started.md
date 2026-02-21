# Getting Started with Development

This guide will help you set up a local development environment for PropManager.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Development Tools](#development-tools)
- [Testing](#testing)
- [Common Tasks](#common-tasks)

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.11+ | Application runtime |
| PostgreSQL | 14+ | Database |
| Redis | 6+ | Cache and task queue |
| Git | 2.x | Version control |

### Optional Software

| Software | Version | Purpose |
|----------|---------|---------|
| Node.js | 18+ | Frontend asset compilation (if modifying) |
| Docker | 24+ | Containerized development |

### System Requirements

- 4GB RAM minimum (8GB recommended)
- 2GB free disk space
- macOS, Linux, or Windows with WSL2

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/propmanager.git
cd propmanager
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 3. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Set Up PostgreSQL

```bash
# Create database and user
sudo -u postgres psql

postgres=# CREATE USER propmanager WITH PASSWORD 'your_password';
postgres=# CREATE DATABASE propmanager OWNER propmanager;
postgres=# GRANT ALL PRIVILEGES ON DATABASE propmanager TO propmanager;
postgres=# \q
```

### 5. Set Up Redis

```bash
# Start Redis (Ubuntu/Debian)
sudo systemctl start redis

# Start Redis (macOS with Homebrew)
brew services start redis

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

---

## Configuration

### Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your local settings:

```bash
# Database
DATABASE_URL=postgres://propmanager:your_password@localhost:5432/propmanager

# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Redis
REDIS_URL=redis://localhost:6379/0

# Email (use console backend for development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### Generate Secret Key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Minimal Development Config

For quick local development, these are the essential settings:

```bash
# .env minimum
DATABASE_URL=postgres://propmanager:password@localhost:5432/propmanager
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=True
REDIS_URL=redis://localhost:6379/0
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

---

## Running the Application

### Apply Migrations

```bash
python manage.py migrate
```

### Create Superuser

```bash
python manage.py createsuperuser
```

Follow the prompts to set email and password.

### Load Development Data (Optional)

```bash
python manage.py seed_dev_data
```

This creates:
- Sample properties and units
- Test tenant accounts
- Invoices and payment history
- Work orders
- Various tenant scenarios for testing

### Start Development Server

```bash
python manage.py runserver
```

Access the application:
- **Admin Portal**: http://localhost:8000/admin-portal/
- **Tenant Portal**: http://localhost:8000/tenant/
- **Django Admin**: http://localhost:8000/admin/

### Start Background Task Worker

In a separate terminal:

```bash
source venv/bin/activate
python manage.py qcluster
```

This runs the Django-Q2 task queue for background jobs.

---

## Development Tools

### Code Formatting

PropManager uses Black and isort for consistent code formatting:

```bash
# Format all Python files
black .

# Sort imports
isort .
```

### Linting

```bash
# Run flake8
flake8

# Run with specific config
flake8 --config=.flake8
```

### Pre-commit Hooks (Recommended)

Install pre-commit for automatic checks:

```bash
pip install pre-commit
pre-commit install
```

### Django Debug Toolbar

Debug toolbar is enabled in development. Access it via the sidebar on any page.

Useful panels:
- **SQL** - Database queries
- **Templates** - Template rendering
- **Cache** - Cache operations
- **Signals** - Signal dispatching

### Django Extensions

Helpful management commands:

```bash
# Interactive shell with auto-imports
python manage.py shell_plus

# Show all URLs
python manage.py show_urls

# Generate model graph
python manage.py graph_models -a -o models.png
```

---

## Testing

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.billing

# Run specific test class
python manage.py test apps.billing.tests.InvoiceTests

# Run with verbosity
python manage.py test -v 2
```

### Test Coverage

```bash
# Run tests with coverage
coverage run --source='.' manage.py test

# Generate report
coverage report

# Generate HTML report
coverage html
# Open htmlcov/index.html in browser
```

### Writing Tests

Place tests in `tests/` directory within each app:

```
apps/billing/
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_views.py
│   └── test_tasks.py
```

Example test:

```python
from django.test import TestCase
from apps.billing.models import Invoice
from apps.leases.models import Lease

class InvoiceModelTest(TestCase):
    def setUp(self):
        # Create test data
        self.lease = Lease.objects.create(...)

    def test_invoice_creation(self):
        invoice = Invoice.objects.create(
            lease=self.lease,
            amount=1000.00
        )
        self.assertEqual(invoice.status, 'draft')

    def test_late_fee_calculation(self):
        # Test late fee logic
        pass
```

---

## Common Tasks

### Creating a New App

```bash
# Create app in apps directory
python manage.py startapp newapp apps/newapp

# Add to INSTALLED_APPS in settings.py
INSTALLED_APPS = [
    ...
    'apps.newapp',
]
```

### Creating Migrations

```bash
# After modifying models
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Check migration SQL without applying
python manage.py sqlmigrate app_name 0001
```

### Resetting the Database

```bash
# Drop and recreate database (development only!)
sudo -u postgres psql -c "DROP DATABASE propmanager;"
sudo -u postgres psql -c "CREATE DATABASE propmanager OWNER propmanager;"

# Run migrations fresh
python manage.py migrate

# Reload seed data
python manage.py seed_dev_data
```

### Viewing Emails

With console email backend, emails are printed to the terminal. For a more realistic experience:

```bash
# Use MailHog (install separately)
# Then set in .env:
EMAIL_HOST=localhost
EMAIL_PORT=1025
```

Access MailHog UI at http://localhost:8025

### Working with the Task Queue

```bash
# View queue info
python manage.py qinfo

# View scheduled tasks
python manage.py qmemory

# Run a specific task manually
python manage.py shell
>>> from django_q.tasks import async_task
>>> async_task('apps.billing.tasks.generate_monthly_invoices')
```

### Accessing Test Accounts

After running `seed_dev_data`:

| Account | Email | Use |
|---------|-------|-----|
| Perfect Payer | perfect_payer@test.com | Always pays on time |
| Chronic Late | chronic_charlie@test.com | Always pays late |
| Overdue Olivia | overdue_olivia@test.com | Has outstanding balance |

Login via OTP - emails appear in console.

---

## IDE Setup

### VS Code

Recommended extensions:
- Python (Microsoft)
- Pylance
- Django (Baptiste Darthenay)
- GitLens

Settings (`.vscode/settings.json`):
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "editor.formatOnSave": true
}
```

### PyCharm

1. Open project folder
2. Configure interpreter: `venv/bin/python`
3. Enable Django support: Settings → Languages & Frameworks → Django
4. Set project root and settings module

---

## Troubleshooting

### Common Issues

**Database connection refused**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check connection
psql -U propmanager -d propmanager
```

**Redis connection error**
```bash
# Check Redis is running
redis-cli ping
```

**Module not found errors**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**Migration errors**
```bash
# Check for conflicting migrations
python manage.py showmigrations

# Reset migrations (development only)
python manage.py migrate app_name zero
python manage.py migrate app_name
```

See [Troubleshooting Guide](../troubleshooting.md) for more solutions.

---

## Next Steps

- Read the [Development Workflow](workflow.md) guide
- Learn about [Background Tasks](tasks.md)
- Review the [Architecture](../architecture.md) documentation
- Check out [Contributing](../../CONTRIBUTING.md) guidelines
