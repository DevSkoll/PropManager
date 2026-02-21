# Troubleshooting Guide

This guide covers common issues and solutions for PropManager.

## Table of Contents

- [Authentication Issues](#authentication-issues)
- [Payment Problems](#payment-problems)
- [Invoice Generation](#invoice-generation)
- [Background Tasks](#background-tasks)
- [Email Delivery](#email-delivery)
- [SMS Delivery](#sms-delivery)
- [Weather API](#weather-api)
- [E-Signature Issues](#e-signature-issues)
- [Database Issues](#database-issues)
- [Performance Issues](#performance-issues)

---

## Authentication Issues

### Tenant Can't Log In

**Symptom:** Tenant reports not receiving magic link email.

**Solutions:**

1. **Check email address**
   - Verify the email is correct in the admin portal
   - Check for typos (e.g., `.con` instead of `.com`)

2. **Check spam folder**
   - Magic links may be filtered as spam
   - Have tenant add your sending domain to contacts

3. **Verify email service**
   ```bash
   python manage.py shell
   >>> from django.core.mail import send_mail
   >>> send_mail('Test', 'Test message', 'noreply@example.com', ['test@example.com'])
   ```
   If this fails, check email configuration.

4. **Check email settings**
   ```bash
   # Verify environment variables
   echo $EMAIL_HOST
   echo $EMAIL_PORT
   echo $EMAIL_HOST_USER
   ```

### Admin Can't Access Portal

**Symptom:** Admin receives "Permission denied" or redirect to login.

**Solutions:**

1. **Verify user is staff**
   ```bash
   python manage.py shell
   >>> from django.contrib.auth import get_user_model
   >>> User = get_user_model()
   >>> user = User.objects.get(email='admin@example.com')
   >>> print(user.is_staff, user.is_active)
   ```

2. **Reset password**
   ```bash
   python manage.py changepassword admin@example.com
   ```

3. **Create new superuser**
   ```bash
   python manage.py createsuperuser
   ```

### Session Expires Too Quickly

**Symptom:** Users are logged out frequently.

**Solution:** Check `SESSION_COOKIE_AGE` in settings:
```python
# settings.py
SESSION_COOKIE_AGE = 86400 * 7  # 7 days
```

---

## Payment Problems

### Stripe Payments Failing

**Symptom:** Stripe payments return error or fail silently.

**Check API Keys:**
```bash
# Verify keys are set
echo $STRIPE_SECRET_KEY
echo $STRIPE_PUBLISHABLE_KEY

# Keys should start with:
# sk_live_ (live secret key)
# pk_live_ (live publishable key)
# sk_test_ (test secret key)
# pk_test_ (test publishable key)
```

**Check Webhook:**
1. Go to Stripe Dashboard → Developers → Webhooks
2. Verify endpoint URL is correct: `https://yourdomain.com/webhooks/stripe/`
3. Check webhook secret matches `STRIPE_WEBHOOK_SECRET`
4. Review recent webhook deliveries for errors

**Common Errors:**

| Error | Cause | Solution |
|-------|-------|----------|
| `card_declined` | Card was declined | Ask tenant to try different card |
| `expired_card` | Card has expired | Update payment method |
| `incorrect_cvc` | Wrong security code | Re-enter card details |
| `processing_error` | Stripe processing issue | Retry later |

### PayPal Payments Not Working

**Symptom:** PayPal buttons don't appear or payments fail.

**Solutions:**

1. **Verify credentials**
   ```bash
   echo $PAYPAL_CLIENT_ID
   echo $PAYPAL_CLIENT_SECRET
   ```

2. **Check sandbox mode**
   - Ensure `PAYPAL_SANDBOX=True` for testing
   - Use sandbox credentials with sandbox mode

3. **Test connectivity**
   ```python
   import paypalrestsdk
   paypalrestsdk.configure({
       "mode": "sandbox",
       "client_id": "YOUR_CLIENT_ID",
       "client_secret": "YOUR_SECRET"
   })
   ```

### ACH/Plaid Issues

**Symptom:** Bank account linking fails.

**Solutions:**

1. **Verify Plaid environment**
   - `sandbox` - Testing only (use test credentials)
   - `development` - Limited live banks
   - `production` - Full access (requires approval)

2. **Check Plaid credentials**
   ```bash
   echo $PLAID_CLIENT_ID
   echo $PLAID_SECRET
   echo $PLAID_ENV
   ```

3. **Test Plaid connection**
   ```python
   from plaid import Client
   client = Client(client_id='xxx', secret='xxx', environment='sandbox')
   # Test with sandbox institution
   ```

### Bitcoin Payments Not Confirming

**Symptom:** Bitcoin payment shows as pending.

**Solutions:**

1. **Check BTCPay Server status**
   - Verify BTCPay Server is running
   - Check node sync status

2. **Verify webhook configuration**
   - BTCPay webhook URL: `https://yourdomain.com/webhooks/btcpay/`
   - Webhook secret must match

3. **Check confirmation settings**
   - Default requires 1 confirmation
   - Network congestion may delay confirmations

---

## Invoice Generation

### Invoices Not Being Generated

**Symptom:** Monthly invoices are not created automatically.

**Check Django-Q2 Status:**
```bash
# Check if cluster is running
python manage.py qinfo

# View scheduled tasks
python manage.py qmemory
```

**Verify Task Schedule:**
```python
from django_q.models import Schedule
for s in Schedule.objects.all():
    print(f"{s.name}: {s.schedule_type} - {s.next_run}")
```

**Run Manually:**
```bash
python manage.py generate_monthly_invoices
```

**Check Lease Status:**
```python
from apps.leases.models import Lease
# Only active leases generate invoices
Lease.objects.filter(status='active').count()
```

### Invoices Have Wrong Amount

**Symptom:** Invoice total doesn't match expected rent.

**Check billing configuration:**
```python
from apps.billing.models import PropertyBillingConfig
config = PropertyBillingConfig.objects.get(property_id=1)
print(f"Late fee: {config.late_fee_type} - {config.late_fee_amount}")
```

**Verify lease fees:**
```python
from apps.leases.models import LeaseFee
fees = LeaseFee.objects.filter(lease_id=1)
for fee in fees:
    print(f"{fee.name}: ${fee.amount} ({fee.frequency})")
```

### Late Fees Not Applied

**Symptom:** Overdue invoices don't have late fees.

**Check grace period:**
```python
config = PropertyBillingConfig.objects.get(property_id=1)
print(f"Grace period: {config.grace_period_days} days")
```

**Run late fee task manually:**
```bash
python manage.py apply_late_fees
```

**Verify invoice status:**
```python
from apps.billing.models import Invoice
from datetime import date
overdue = Invoice.objects.filter(
    status='sent',
    due_date__lt=date.today()
)
print(f"Overdue invoices: {overdue.count()}")
```

---

## Background Tasks

### Django-Q2 Cluster Not Running

**Symptom:** Background tasks are not executing.

**Start the cluster:**
```bash
python manage.py qcluster
```

**Check for errors:**
```bash
# View cluster logs
tail -f logs/qcluster.log
```

**Verify Redis connection:**
```bash
redis-cli ping
# Should return PONG
```

### Tasks Stuck in Queue

**Symptom:** Tasks are queued but not processing.

**Check queue status:**
```bash
python manage.py qinfo
```

**Clear stuck tasks:**
```python
from django_q.models import OrmQ
# View pending tasks
OrmQ.objects.all()

# Clear all pending (use with caution)
OrmQ.objects.all().delete()
```

### Task Failures

**Symptom:** Tasks fail with errors.

**View failed tasks:**
```python
from django_q.models import Failure
for f in Failure.objects.all()[:10]:
    print(f"{f.name}: {f.result}")
```

**Retry failed task:**
```python
from django_q.models import Failure
failure = Failure.objects.last()
# Examine and fix the issue, then retry manually
```

---

## Email Delivery

### Emails Not Sending

**Symptom:** No emails are being delivered.

**Check configuration:**
```python
from django.conf import settings
print(settings.EMAIL_BACKEND)
print(settings.EMAIL_HOST)
print(settings.EMAIL_PORT)
```

**Test email sending:**
```bash
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail(
...     'Test Subject',
...     'Test body',
...     'from@example.com',
...     ['to@example.com'],
...     fail_silently=False,
... )
```

**Common issues:**

| Issue | Solution |
|-------|----------|
| Connection refused | Check EMAIL_HOST and EMAIL_PORT |
| Authentication failed | Verify EMAIL_HOST_USER and PASSWORD |
| SSL/TLS error | Check EMAIL_USE_TLS or EMAIL_USE_SSL |
| Timeout | Increase EMAIL_TIMEOUT setting |

### Emails Going to Spam

**Solutions:**

1. **Set up SPF record**
   ```
   v=spf1 include:_spf.youremailprovider.com ~all
   ```

2. **Set up DKIM**
   - Configure with your email provider
   - Add DKIM record to DNS

3. **Set up DMARC**
   ```
   v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com
   ```

4. **Use consistent From address**
   - Always send from the same domain
   - Match From header with authenticated domain

---

## SMS Delivery

### Twilio SMS Not Sending

**Symptom:** SMS messages are not delivered.

**Verify credentials:**
```bash
echo $TWILIO_ACCOUNT_SID
echo $TWILIO_AUTH_TOKEN
echo $TWILIO_PHONE_NUMBER
```

**Test SMS:**
```python
from twilio.rest import Client
client = Client(account_sid, auth_token)
message = client.messages.create(
    body="Test message",
    from_="+15551234567",
    to="+15559876543"
)
print(message.sid)
```

**Common errors:**

| Error | Cause | Solution |
|-------|-------|----------|
| 21211 | Invalid 'To' number | Verify phone number format |
| 21608 | Unverified number | Verify number in Twilio console |
| 21614 | Not a mobile number | SMS only works with mobile numbers |
| 20003 | Auth failure | Check credentials |

### SMS Rate Limiting

**Symptom:** Some messages aren't delivered.

**Solutions:**

1. **Check Twilio logs** in console
2. **Implement rate limiting** in your code
3. **Use messaging service** for higher throughput
4. **Upgrade Twilio account** if needed

---

## Weather API

### Weather Data Not Loading

**Symptom:** Weather notifications not working.

**Verify API key:**
```bash
echo $OPENWEATHERMAP_API_KEY
```

**Test API:**
```bash
curl "https://api.openweathermap.org/data/2.5/weather?q=London&appid=YOUR_API_KEY"
```

**Check rate limits:**
- Free tier: 60 calls/minute
- Monitor API usage in OpenWeatherMap dashboard

### Incorrect Weather Alerts

**Symptom:** Alerts triggered for wrong conditions.

**Check alert thresholds:**
```python
from apps.communications.models import WeatherConfig
config = WeatherConfig.objects.first()
print(f"Heat threshold: {config.heat_threshold}")
print(f"Cold threshold: {config.cold_threshold}")
```

---

## E-Signature Issues

### Signing Link Expired

**Symptom:** Tenant receives "Link Expired" message.

**Solution:** Links expire after 7 days. Resend the signing request:

1. Go to lease detail in admin portal
2. Click "Send for Signatures" again
3. New links will be generated and sent

### Signature Not Saving

**Symptom:** Tenant completes signing but signature doesn't save.

**Check:**

1. **JavaScript errors** - Check browser console
2. **Canvas support** - Ensure browser supports HTML5 canvas
3. **Network errors** - Check for failed API requests

**Debug:**
```python
from apps.leases.models import LeaseSignature
sig = LeaseSignature.objects.last()
print(f"Signed: {sig.signed_at}")
print(f"Has image: {bool(sig.signature_image)}")
```

### All Signatures Complete But Lease Not Executed

**Symptom:** All parties signed but status isn't "executed".

**Check signature status:**
```python
from apps.leases.models import Lease, LeaseSignature
lease = Lease.objects.get(pk=1)
sigs = LeaseSignature.objects.filter(lease=lease)
for sig in sigs:
    print(f"{sig.signer_name}: {'Signed' if sig.signed_at else 'Pending'}")
```

**Manually update if needed:**
```python
lease.signature_status = 'executed'
lease.fully_executed_at = timezone.now()
lease.save()
```

---

## Database Issues

### Migration Errors

**Symptom:** `migrate` command fails.

**Solutions:**

1. **Check migration status**
   ```bash
   python manage.py showmigrations
   ```

2. **Fake problematic migration** (if already applied manually)
   ```bash
   python manage.py migrate app_name migration_name --fake
   ```

3. **Reset migrations** (development only)
   ```bash
   python manage.py migrate app_name zero
   python manage.py migrate app_name
   ```

### Connection Errors

**Symptom:** "Could not connect to database" errors.

**Check PostgreSQL:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -h localhost -U propmanager -d propmanager
```

**Verify settings:**
```python
from django.conf import settings
print(settings.DATABASES['default'])
```

### Performance Issues

**Symptom:** Database queries are slow.

**Identify slow queries:**
```python
from django.db import connection
print(connection.queries[-10:])  # Last 10 queries
```

**Add indexes:**
```python
class Meta:
    indexes = [
        models.Index(fields=['status', 'due_date']),
    ]
```

---

## Performance Issues

### Slow Page Loads

**Check:**

1. **Database queries** - Use Django Debug Toolbar
2. **N+1 queries** - Add `select_related()` and `prefetch_related()`
3. **Caching** - Implement Redis caching for frequent queries

**Enable query logging:**
```python
LOGGING = {
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}
```

### High Memory Usage

**Solutions:**

1. **Paginate large querysets**
   ```python
   from django.core.paginator import Paginator
   paginator = Paginator(Invoice.objects.all(), 100)
   ```

2. **Use `iterator()` for large datasets**
   ```python
   for invoice in Invoice.objects.all().iterator():
       process(invoice)
   ```

3. **Check for memory leaks** in background tasks

### Redis Connection Issues

**Symptom:** Caching or task queue fails.

**Check Redis:**
```bash
redis-cli ping
redis-cli info memory
```

**Test from Django:**
```python
from django.core.cache import cache
cache.set('test', 'value', 60)
print(cache.get('test'))
```

---

## Getting Help

If you can't resolve an issue:

1. **Check logs** - `logs/` directory
2. **Search issues** - GitHub issues for similar problems
3. **Ask for help** - Create a GitHub issue with:
   - PropManager version
   - Python/Django version
   - Full error message
   - Steps to reproduce
