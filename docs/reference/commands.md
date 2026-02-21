# Management Commands Reference

This document covers PropManager's custom Django management commands.

## Table of Contents

- [Overview](#overview)
- [Development Commands](#development-commands)
- [Billing Commands](#billing-commands)
- [Communication Commands](#communication-commands)
- [Maintenance Commands](#maintenance-commands)
- [Django-Q2 Commands](#django-q2-commands)

---

## Overview

### Running Commands

All commands are run using Django's `manage.py`:

```bash
python manage.py <command_name> [options]
```

### Getting Help

View help for any command:

```bash
python manage.py <command_name> --help
```

---

## Development Commands

### seed_dev_data

Creates comprehensive test data for development and testing.

```bash
python manage.py seed_dev_data
```

**What it creates:**
- 5 properties with varying configurations
- 29 units across all properties
- 15 tenants with different payment behaviors
- 12 months of invoice history
- Payments matching tenant scenarios
- Active leases with signatures
- Work orders in various states
- Reward configurations

**Tenant Scenarios:**

| Username | Scenario | Payment Behavior |
|----------|----------|------------------|
| `perfect_payer` | On-time payer | Always pays on time |
| `chronic_charlie` | Chronic late | Always pays late |
| `overdue_olivia` | Outstanding balance | Has delinquent invoices |
| `newbie_nick` | New tenant | Just moved in |
| `auto_alice` | AutoPay enabled | Automatic payments |
| `partial_pat` | Partial payments | Pays in installments |
| `prepay_pete` | Prepays rent | Pays months ahead |
| `streak_sally` | Long streak | 12+ month payment streak |

**Options:**

| Option | Description |
|--------|-------------|
| `--clear` | Clear existing data before seeding |
| `--no-input` | Skip confirmation prompts |

**Example:**
```bash
# Fresh seed with data clearing
python manage.py seed_dev_data --clear --no-input
```

---

## Billing Commands

### generate_monthly_invoices

Generates monthly rent invoices for all active leases.

```bash
python manage.py generate_monthly_invoices
```

**Process:**
1. Finds all active leases
2. Checks if invoice already exists for the month
3. Creates invoice with:
   - Base rent amount
   - Additional fees (pet rent, parking, etc.)
   - Correct due date based on lease terms
4. Sends notification to tenant

**Options:**

| Option | Description |
|--------|-------------|
| `--dry-run` | Show what would be created without creating |
| `--property <id>` | Generate for specific property only |
| `--month <YYYY-MM>` | Generate for specific month |

**Examples:**
```bash
# Preview what would be generated
python manage.py generate_monthly_invoices --dry-run

# Generate for specific property
python manage.py generate_monthly_invoices --property 1

# Generate for specific month
python manage.py generate_monthly_invoices --month 2025-03
```

### apply_late_fees

Applies late fees to overdue invoices based on property billing configuration.

```bash
python manage.py apply_late_fees
```

**Process:**
1. Finds overdue, unpaid invoices
2. Checks if grace period has passed
3. Calculates late fee based on PropertyBillingConfig:
   - Flat fee: Fixed dollar amount
   - Percentage: Percentage of amount due
4. Adds late fee line item to invoice
5. Notifies tenant

**Options:**

| Option | Description |
|--------|-------------|
| `--dry-run` | Show what would be applied without applying |
| `--property <id>` | Apply for specific property only |

**Example:**
```bash
# Preview late fees
python manage.py apply_late_fees --dry-run
```

### send_payment_reminders

Sends payment reminders for upcoming and overdue invoices.

```bash
python manage.py send_payment_reminders
```

**Process:**
1. Finds invoices with upcoming due dates (3 days, 1 day)
2. Finds overdue invoices (1 day, 7 days, 30 days)
3. Sends reminders via configured channels (email, SMS)
4. Records reminder in notification history

**Options:**

| Option | Description |
|--------|-------------|
| `--dry-run` | Show what would be sent without sending |
| `--days-before <n>` | Override days before due date |
| `--days-after <n>` | Override days after due date |

---

## Communication Commands

### check_weather_alerts

Checks weather conditions and sends alerts if thresholds are met.

```bash
python manage.py check_weather_alerts
```

**Process:**
1. Fetches current weather for each property location
2. Compares against configured thresholds:
   - Extreme heat
   - Extreme cold
   - High winds
   - Severe weather
3. Sends alerts to affected tenants
4. Records alerts sent to prevent duplicates

**Options:**

| Option | Description |
|--------|-------------|
| `--dry-run` | Show alerts without sending |
| `--property <id>` | Check specific property only |

**Example:**
```bash
python manage.py check_weather_alerts --dry-run
```

### send_notification

Sends a notification to specified recipients.

```bash
python manage.py send_notification --to <recipient> --subject <subject> --body <body>
```

**Options:**

| Option | Description |
|--------|-------------|
| `--to <email>` | Recipient email address |
| `--group <name>` | Send to notification group |
| `--subject <text>` | Notification subject |
| `--body <text>` | Notification body |
| `--channel <type>` | Channel: email, sms, in_app |

**Examples:**
```bash
# Send email to specific user
python manage.py send_notification --to tenant@example.com \
    --subject "Test" --body "Test message" --channel email

# Send to notification group
python manage.py send_notification --group "All Tenants" \
    --subject "Announcement" --body "Important update"
```

---

## Maintenance Commands

### expire_signing_links

Expires old lease signing links for security.

```bash
python manage.py expire_signing_links
```

**Process:**
1. Finds signatures with tokens older than 7 days
2. Marks tokens as expired
3. Logs expired tokens count

**Options:**

| Option | Description |
|--------|-------------|
| `--days <n>` | Override expiration days (default: 7) |
| `--dry-run` | Show what would be expired |

### cleanup_old_tasks

Cleans up old completed and failed tasks from Django-Q2.

```bash
python manage.py cleanup_old_tasks
```

**Options:**

| Option | Description |
|--------|-------------|
| `--days <n>` | Delete tasks older than N days (default: 30) |
| `--failures-only` | Only clean up failed tasks |

### calculate_rewards

Calculates and grants tenant rewards.

```bash
python manage.py calculate_rewards
```

**Process:**
1. Checks all active tenants
2. Calculates payment streaks
3. Checks for prepayment bonuses
4. Grants applicable rewards
5. Records in reward history

**Options:**

| Option | Description |
|--------|-------------|
| `--dry-run` | Show rewards without granting |
| `--tenant <id>` | Calculate for specific tenant |

---

## Django-Q2 Commands

These commands are provided by Django-Q2 for task queue management.

### qcluster

Starts the Django-Q2 cluster for processing background tasks.

```bash
python manage.py qcluster
```

This is the main process for handling background tasks. Run this in a separate terminal or as a systemd service.

**Key behaviors:**
- Connects to Redis
- Starts worker processes
- Processes queued tasks
- Executes scheduled tasks

### qinfo

Displays information about the Django-Q2 cluster.

```bash
python manage.py qinfo
```

**Output includes:**
- Cluster status
- Number of workers
- Queued tasks
- Recent task activity

### qmemory

Shows memory usage of the cluster.

```bash
python manage.py qmemory
```

### qmonitor

Real-time monitoring of the cluster.

```bash
python manage.py qmonitor
```

Shows live updates of:
- Task processing
- Queue depth
- Worker status

Press `Ctrl+C` to exit.

### qflush

Clears the task queue. **Use with caution!**

```bash
python manage.py qflush
```

This removes all pending tasks from the queue.

---

## Creating Custom Commands

### Command Structure

Place commands in `apps/<app>/management/commands/`:

```
apps/billing/
├── management/
│   ├── __init__.py
│   └── commands/
│       ├── __init__.py
│       └── my_command.py
```

### Command Template

```python
# apps/billing/management/commands/my_command.py

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Description of what this command does'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes',
        )
        parser.add_argument(
            '--property',
            type=int,
            help='Property ID to process',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        property_id = options.get('property')

        if dry_run:
            self.stdout.write('Dry run mode - no changes will be made')

        # Command logic here
        items_processed = self.process_items(property_id, dry_run)

        self.stdout.write(
            self.style.SUCCESS(f'Processed {items_processed} items')
        )

    def process_items(self, property_id, dry_run):
        # Implementation
        return 0
```

### Styling Output

```python
# Success message (green)
self.stdout.write(self.style.SUCCESS('Operation completed'))

# Warning message (yellow)
self.stdout.write(self.style.WARNING('Check this'))

# Error message (red)
self.stdout.write(self.style.ERROR('Something failed'))

# Regular output
self.stdout.write('Processing...')
```

### Progress Output

For long-running commands:

```python
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        items = get_items()
        total = len(items)

        for i, item in enumerate(items, 1):
            self.process_item(item)
            self.stdout.write(f'Processed {i}/{total}', ending='\r')
            self.stdout.flush()

        self.stdout.write('')  # New line after progress
        self.stdout.write(self.style.SUCCESS('Done!'))
```

---

## Scheduling Commands

### Via Cron

```bash
# /etc/cron.d/propmanager

# Generate invoices on the 1st of each month at midnight
0 0 1 * * propmanager cd /opt/propmanager && venv/bin/python manage.py generate_monthly_invoices

# Apply late fees daily at 9 AM
0 9 * * * propmanager cd /opt/propmanager && venv/bin/python manage.py apply_late_fees

# Check weather every 6 hours
0 */6 * * * propmanager cd /opt/propmanager && venv/bin/python manage.py check_weather_alerts
```

### Via Django-Q2

Schedule in admin or programmatically:

```python
from django_q.models import Schedule

Schedule.objects.create(
    name='Generate Monthly Invoices',
    func='apps.billing.tasks.generate_monthly_invoices',
    schedule_type=Schedule.MONTHLY,
    repeats=-1,
)
```

---

## Further Reading

- [Background Tasks](../development/tasks.md) - Django-Q2 guide
- [Troubleshooting](../troubleshooting.md) - Common issues
- [Getting Started](../development/getting-started.md) - Development setup
