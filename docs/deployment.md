# Deployment Guide

## Production Environment Setup

### 1. System Requirements

- Python 3.10+
- PostgreSQL 14+
- Nginx (recommended reverse proxy)
- Supervisor or systemd (for process management)

### 2. Clone and Install

```bash
git clone <repository-url> /opt/propmanager
cd /opt/propmanager/propmanager
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/base.txt
```

### 3. Environment Configuration

Create `/opt/propmanager/propmanager/.env`:

```bash
# Required
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=<generate-a-64-char-random-string>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgres://propmanager:password@localhost:5432/propmanager

# Email (SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Twilio (for SMS OTP and notifications)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+15551234567

# Payment Gateways (configure via admin UI, but env vars needed for keys)
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

PAYPAL_CLIENT_ID=xxx
PAYPAL_CLIENT_SECRET=xxx
PAYPAL_MODE=live

SQUARE_ACCESS_TOKEN=xxx
SQUARE_ENVIRONMENT=production
SQUARE_LOCATION_ID=xxx

# Weather
OPENWEATHERMAP_API_KEY=your_api_key
```

Generate a secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 4. Database Setup

```bash
# Create PostgreSQL database
sudo -u postgres createuser propmanager
sudo -u postgres createdb propmanager -O propmanager
sudo -u postgres psql -c "ALTER USER propmanager WITH PASSWORD 'your-secure-password';"

# Run migrations
source venv/bin/activate
python manage.py migrate

# Create admin account
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --no-input
```

### 5. Gunicorn (WSGI Server)

Install:

```bash
pip install gunicorn
```

Create `/etc/systemd/system/propmanager.service`:

```ini
[Unit]
Description=PropManager Django Application
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/propmanager/propmanager
ExecStart=/opt/propmanager/propmanager/venv/bin/gunicorn \
    config.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 3 \
    --timeout 120
Restart=always
EnvironmentFile=/opt/propmanager/propmanager/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable propmanager
sudo systemctl start propmanager
```

### 6. Django-Q2 Worker

Create `/etc/systemd/system/propmanager-worker.service`:

```ini
[Unit]
Description=PropManager Django-Q2 Worker
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/propmanager/propmanager
ExecStart=/opt/propmanager/propmanager/venv/bin/python manage.py qcluster
Restart=always
EnvironmentFile=/opt/propmanager/propmanager/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable propmanager-worker
sudo systemctl start propmanager-worker
```

### 7. Nginx Configuration

Create `/etc/nginx/sites-available/propmanager`:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    client_max_body_size 20M;

    location /static/ {
        alias /opt/propmanager/propmanager/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /opt/propmanager/propmanager/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/propmanager /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 8. SSL with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## Production Settings

The production settings (`config/settings/production.py`) automatically enable:

- `SECURE_SSL_REDIRECT = True`
- `SECURE_HSTS_SECONDS = 31536000` (1 year)
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- `SECURE_BROWSER_XSS_FILTER = True`
- `SECURE_CONTENT_TYPE_NOSNIFF = True`
- PostgreSQL database via `DATABASE_URL`

---

## Environment Variables Reference

### Required (Production)

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | Django secret key (64+ chars) | `abc123...` |
| `ALLOWED_HOSTS` | Comma-separated hostnames | `yourdomain.com,www.yourdomain.com` |
| `DATABASE_URL` | PostgreSQL connection string | `postgres://user:pass@host:5432/db` |

### Email

| Variable | Default | Description |
|---|---|---|
| `EMAIL_BACKEND` | Console backend | Django email backend class |
| `EMAIL_HOST` | `smtp.gmail.com` | SMTP server |
| `EMAIL_PORT` | `587` | SMTP port |
| `EMAIL_USE_TLS` | `True` | Use TLS |
| `EMAIL_HOST_USER` | `""` | SMTP username |
| `EMAIL_HOST_PASSWORD` | `""` | SMTP password |
| `DEFAULT_FROM_EMAIL` | `noreply@propmanager.com` | Sender address |

### Twilio (SMS)

| Variable | Default | Description |
|---|---|---|
| `TWILIO_ACCOUNT_SID` | `""` | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | `""` | Twilio Auth Token |
| `TWILIO_PHONE_NUMBER` | `""` | Twilio sender phone number |

### Payment Gateways

| Variable | Description |
|---|---|
| `STRIPE_SECRET_KEY` | Stripe secret API key |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key (frontend) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook endpoint secret |
| `PAYPAL_CLIENT_ID` | PayPal REST API client ID |
| `PAYPAL_CLIENT_SECRET` | PayPal REST API secret |
| `PAYPAL_MODE` | `sandbox` or `live` |
| `SQUARE_ACCESS_TOKEN` | Square API access token |
| `SQUARE_ENVIRONMENT` | `sandbox` or `production` |
| `SQUARE_LOCATION_ID` | Square location ID |

### Weather

| Variable | Default | Description |
|---|---|---|
| `OPENWEATHERMAP_API_KEY` | `""` | OpenWeatherMap API key |

### Django

| Variable | Default | Description |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` | Settings module path |
| `DEBUG` | `False` | Debug mode (never True in production) |

---

## Backup Strategy

### Database

```bash
# Daily PostgreSQL backup
pg_dump propmanager > /backups/propmanager_$(date +%Y%m%d).sql

# Restore
psql propmanager < /backups/propmanager_20250301.sql
```

### Media Files

```bash
# Backup uploaded files
rsync -av /opt/propmanager/propmanager/media/ /backups/media/
```

---

## Monitoring

### Check application health

```bash
# Application running
sudo systemctl status propmanager

# Worker running
sudo systemctl status propmanager-worker

# Recent logs
sudo journalctl -u propmanager -n 50

# Django-Q2 task queue status
python manage.py qinfo
```

### Django System Check

```bash
python manage.py check --deploy
```

This validates all production security settings are correctly configured.

---

## Updating

```bash
cd /opt/propmanager
git pull origin main
source propmanager/venv/bin/activate
cd propmanager
pip install -r requirements/base.txt
python manage.py migrate
python manage.py collectstatic --no-input
sudo systemctl restart propmanager
sudo systemctl restart propmanager-worker
```
