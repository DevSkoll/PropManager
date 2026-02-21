# Background Tasks with Django-Q2

PropManager uses Django-Q2 for background task processing. This guide covers how to create, schedule, and monitor tasks.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Running the Cluster](#running-the-cluster)
- [Creating Tasks](#creating-tasks)
- [Scheduling Tasks](#scheduling-tasks)
- [Task Hooks](#task-hooks)
- [Error Handling](#error-handling)
- [Monitoring](#monitoring)
- [Testing Tasks](#testing-tasks)
- [Best Practices](#best-practices)

---

## Overview

### What is Django-Q2?

Django-Q2 is a task queue for Django that provides:

- **Async task execution** - Run tasks in the background
- **Scheduled tasks** - Cron-like scheduling
- **Task chaining** - Run tasks in sequence
- **Result storage** - Store and retrieve task results
- **Admin integration** - Monitor tasks via Django admin

### When to Use Background Tasks

Use background tasks for:

- **Long-running operations** - Report generation, bulk emails
- **Scheduled jobs** - Invoice generation, late fee application
- **External API calls** - Payment processing, SMS sending
- **Resource-intensive work** - Data processing, file generation

---

## Architecture

### Components

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Django App    │────▶│   Redis Queue   │────▶│  Q Cluster      │
│   (Producer)    │     │   (Broker)      │     │  (Consumer)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                       │
                                                       ▼
                                               ┌─────────────────┐
                                               │   PostgreSQL    │
                                               │   (Results)     │
                                               └─────────────────┘
```

### Configuration

Django-Q2 is configured in settings:

```python
# settings.py
Q_CLUSTER = {
    'name': 'propmanager',
    'workers': 4,
    'recycle': 500,
    'timeout': 60,
    'compress': True,
    'save_limit': 250,
    'queue_limit': 500,
    'cpu_affinity': 1,
    'label': 'Django Q',
    'redis': {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
    }
}
```

### Key Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `workers` | CPU count | Number of worker processes |
| `timeout` | 60 | Task timeout in seconds |
| `recycle` | 500 | Recycle workers after N tasks |
| `save_limit` | 250 | Max successful tasks to keep |
| `retry` | None | Retry failed tasks N times |

---

## Running the Cluster

### Development

```bash
# Start the cluster
python manage.py qcluster
```

The cluster will:
- Connect to Redis
- Start worker processes
- Begin processing tasks
- Execute scheduled tasks

### Production (systemd)

Create a systemd service:

```ini
# /etc/systemd/system/propmanager-qcluster.service
[Unit]
Description=PropManager Django-Q2 Cluster
After=network.target

[Service]
User=propmanager
Group=propmanager
WorkingDirectory=/opt/propmanager
ExecStart=/opt/propmanager/venv/bin/python manage.py qcluster
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable propmanager-qcluster
sudo systemctl start propmanager-qcluster
```

### Monitoring Cluster Status

```bash
# View cluster info
python manage.py qinfo

# View memory usage
python manage.py qmemory
```

---

## Creating Tasks

### Basic Task

Create tasks as regular Python functions:

```python
# apps/billing/tasks.py

def generate_invoice_for_lease(lease_id):
    """Generate monthly invoice for a specific lease."""
    from apps.leases.models import Lease
    from apps.billing.models import Invoice

    lease = Lease.objects.get(pk=lease_id)
    invoice = Invoice.objects.create(
        lease=lease,
        amount=lease.monthly_rent,
        due_date=calculate_due_date(lease)
    )
    return invoice.id
```

### Calling Tasks Asynchronously

```python
from django_q.tasks import async_task

# Queue a task
task_id = async_task('apps.billing.tasks.generate_invoice_for_lease',
                     lease_id=123)

# With custom options
task_id = async_task(
    'apps.billing.tasks.generate_invoice_for_lease',
    lease_id=123,
    timeout=120,          # Custom timeout
    task_name='invoice-lease-123',  # Descriptive name
    group='billing',      # Task group for organization
)
```

### Task with Return Value

```python
from django_q.tasks import async_task, result

# Queue task
task_id = async_task('apps.billing.tasks.calculate_total_revenue')

# Later, get the result
revenue = result(task_id, wait=5000)  # Wait up to 5 seconds
```

### Task Chain

Run tasks in sequence:

```python
from django_q.tasks import async_chain

# Each task receives the previous task's result
async_chain([
    ('apps.billing.tasks.generate_invoices', ()),
    ('apps.billing.tasks.send_invoice_emails', ()),
    ('apps.billing.tasks.log_billing_run', ()),
])
```

### Task with Hook

Execute a callback when task completes:

```python
async_task(
    'apps.billing.tasks.generate_invoice_for_lease',
    lease_id=123,
    hook='apps.billing.tasks.on_invoice_generated'
)
```

---

## Scheduling Tasks

### Using the Admin

1. Go to Django Admin → Django Q → Scheduled tasks
2. Click "Add"
3. Configure:
   - **Name** - Descriptive name
   - **Func** - Full path to function
   - **Schedule Type** - Daily, Hourly, Minutes, Cron
   - **Repeats** - Number of times to run (-1 for infinite)

### Programmatic Scheduling

```python
from django_q.models import Schedule

# Run daily at midnight
Schedule.objects.create(
    name='Generate Monthly Invoices',
    func='apps.billing.tasks.generate_monthly_invoices',
    schedule_type=Schedule.DAILY,
    repeats=-1,  # Run forever
)

# Run every hour
Schedule.objects.create(
    name='Check Weather Alerts',
    func='apps.communications.tasks.check_weather_alerts',
    schedule_type=Schedule.HOURLY,
    repeats=-1,
)

# Run at specific times (cron syntax)
Schedule.objects.create(
    name='Apply Late Fees',
    func='apps.billing.tasks.apply_late_fees',
    schedule_type=Schedule.CRON,
    cron='0 9 * * *',  # 9 AM daily
    repeats=-1,
)
```

### Schedule Types

| Type | Usage | Example |
|------|-------|---------|
| `ONCE` | Single execution | One-time migration |
| `MINUTES` | Every N minutes | `minutes=15` |
| `HOURLY` | Every hour | Sync tasks |
| `DAILY` | Once per day | Report generation |
| `WEEKLY` | Once per week | Weekly digest |
| `MONTHLY` | Once per month | Monthly billing |
| `QUARTERLY` | Every 3 months | Quarterly reports |
| `YEARLY` | Once per year | Annual tasks |
| `CRON` | Cron expression | Complex schedules |

### PropManager Scheduled Tasks

| Task | Schedule | Purpose |
|------|----------|---------|
| `generate_monthly_invoices` | Monthly, 1st | Create rent invoices |
| `apply_late_fees` | Daily, 9 AM | Apply late fees to overdue invoices |
| `calculate_rewards` | Daily | Grant reward points |
| `check_weather_alerts` | Every 6 hours | Monitor weather conditions |
| `send_payment_reminders` | Daily, 10 AM | Remind tenants of upcoming payments |
| `expire_signing_links` | Daily | Clean up expired signature tokens |

---

## Task Hooks

### Creating a Hook

Hooks are called when a task completes:

```python
# apps/billing/tasks.py

def on_invoice_generated(task):
    """Called when invoice generation completes."""
    if task.success:
        invoice_id = task.result
        # Send notification, log success, etc.
        send_invoice_notification(invoice_id)
    else:
        # Handle failure
        log_invoice_failure(task.name, task.result)
```

### Hook Parameters

The hook receives a `Task` object with:

| Attribute | Description |
|-----------|-------------|
| `task.name` | Task name |
| `task.func` | Function path |
| `task.args` | Positional arguments |
| `task.kwargs` | Keyword arguments |
| `task.result` | Return value or error |
| `task.success` | Boolean success status |
| `task.time_taken` | Execution time |
| `task.started` | Start timestamp |
| `task.stopped` | Stop timestamp |

---

## Error Handling

### Task-Level Error Handling

```python
def risky_task(data):
    """Task with proper error handling."""
    try:
        result = process_data(data)
        return {'status': 'success', 'result': result}
    except ValidationError as e:
        # Return error info instead of raising
        return {'status': 'error', 'message': str(e)}
    except Exception as e:
        # Log and re-raise for retry
        logger.exception("Task failed")
        raise
```

### Automatic Retry

Configure retry in Q_CLUSTER or per-task:

```python
# Global retry
Q_CLUSTER = {
    'retry': 60,  # Retry after 60 seconds
}

# Per-task retry
async_task(
    'apps.billing.tasks.process_payment',
    payment_id=123,
    retry=120,  # Retry after 2 minutes
)
```

### Failed Task Handling

```python
from django_q.models import Failure

# View failed tasks
failures = Failure.objects.all()

for failure in failures:
    print(f"Task: {failure.name}")
    print(f"Error: {failure.result}")
    print(f"Time: {failure.started}")
```

### Cleanup Old Failures

```python
from datetime import timedelta
from django.utils import timezone
from django_q.models import Failure

# Delete failures older than 30 days
cutoff = timezone.now() - timedelta(days=30)
Failure.objects.filter(started__lt=cutoff).delete()
```

---

## Monitoring

### Django Admin

Django-Q2 provides admin views:

- **Scheduled tasks** - View and manage schedules
- **Successful tasks** - View completed tasks
- **Failed tasks** - View and retry failures
- **Queued tasks** - View pending tasks

### Command Line

```bash
# Cluster information
python manage.py qinfo

# Memory usage
python manage.py qmemory

# Monitor (real-time updates)
python manage.py qmonitor
```

### Programmatic Monitoring

```python
from django_q.monitor import Stat

# Get cluster statistics
stats = Stat.get_all()
for stat in stats:
    print(f"Cluster: {stat.cluster_id}")
    print(f"Workers: {stat.workers}")
    print(f"Queued: {stat.task_q_size}")
```

### Logging

Configure logging for task visibility:

```python
LOGGING = {
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django-q': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
```

---

## Testing Tasks

### Unit Testing Tasks

Test task functions directly:

```python
from django.test import TestCase
from apps.billing.tasks import generate_invoice_for_lease
from apps.leases.models import Lease

class InvoiceTaskTests(TestCase):
    def setUp(self):
        self.lease = LeaseFactory.create()

    def test_generate_invoice_creates_invoice(self):
        invoice_id = generate_invoice_for_lease(self.lease.id)

        from apps.billing.models import Invoice
        invoice = Invoice.objects.get(pk=invoice_id)

        self.assertEqual(invoice.lease, self.lease)
        self.assertEqual(invoice.amount, self.lease.monthly_rent)
```

### Testing Async Execution

Use synchronous mode for testing:

```python
# settings/test.py
Q_CLUSTER = {
    'name': 'test',
    'sync': True,  # Run tasks synchronously
}
```

```python
from django.test import TestCase, override_settings
from django_q.tasks import async_task

class AsyncTaskTests(TestCase):
    @override_settings(Q_CLUSTER={'sync': True})
    def test_async_task_execution(self):
        # Task runs synchronously in tests
        task_id = async_task('apps.billing.tasks.generate_invoice')
        # Result is immediately available
```

### Testing Scheduled Tasks

```python
from django.test import TestCase
from django_q.models import Schedule

class ScheduleTests(TestCase):
    def test_billing_schedule_exists(self):
        schedule = Schedule.objects.get(name='Generate Monthly Invoices')

        self.assertEqual(schedule.schedule_type, Schedule.MONTHLY)
        self.assertEqual(schedule.func, 'apps.billing.tasks.generate_monthly_invoices')
```

---

## Best Practices

### Task Design

1. **Keep tasks simple** - Do one thing well
2. **Make tasks idempotent** - Safe to run multiple times
3. **Accept IDs, not objects** - Avoid serialization issues
4. **Handle failures gracefully** - Log and notify
5. **Set appropriate timeouts** - Don't block the queue

### Idempotent Tasks

```python
def send_invoice_email(invoice_id):
    """Idempotent: safe to run multiple times."""
    from apps.billing.models import Invoice

    invoice = Invoice.objects.get(pk=invoice_id)

    # Check if already sent
    if invoice.email_sent_at:
        return {'status': 'already_sent'}

    # Send email
    send_email(invoice)

    # Mark as sent
    invoice.email_sent_at = timezone.now()
    invoice.save()

    return {'status': 'sent'}
```

### Avoiding Common Issues

**Don't pass Django objects:**
```python
# Bad - object may change or fail to serialize
async_task('task', invoice=invoice)

# Good - pass ID and fetch fresh
async_task('task', invoice_id=invoice.id)
```

**Don't assume database state:**
```python
# Bad - object may be deleted
def task(invoice_id):
    invoice = Invoice.objects.get(pk=invoice_id)

# Good - handle missing objects
def task(invoice_id):
    try:
        invoice = Invoice.objects.get(pk=invoice_id)
    except Invoice.DoesNotExist:
        logger.warning(f"Invoice {invoice_id} not found")
        return
```

**Set reasonable timeouts:**
```python
# Task-specific timeout for long operations
async_task(
    'apps.reports.tasks.generate_annual_report',
    year=2024,
    timeout=600,  # 10 minutes
)
```

### Performance

1. **Batch operations** - Process multiple items in one task
2. **Use task groups** - Organize related tasks
3. **Monitor queue depth** - Scale workers as needed
4. **Clean up old results** - Prevent database bloat

---

## Reference

### Useful Commands

```bash
# Start cluster
python manage.py qcluster

# View info
python manage.py qinfo

# Monitor real-time
python manage.py qmonitor

# Clear queue (use with caution)
python manage.py qflush
```

### Further Reading

- [Django-Q2 Documentation](https://django-q2.readthedocs.io/)
- [Getting Started](getting-started.md)
- [Troubleshooting](../troubleshooting.md)
