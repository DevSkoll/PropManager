# Deployment Guide

This guide covers production deployment of PropManager using **Docker** (recommended) or **traditional** (systemd + Gunicorn) methods.

---

## Deployment Methods

| Method | Best For | Complexity | Features |
|--------|----------|------------|----------|
| [Docker Production](#docker-production) | Modern deployments, cloud hosting | Low | Isolated, reproducible, easy updates |
| [Traditional Deployment](#traditional-deployment) | VPS, dedicated servers | Medium | Full control, systemd integration |

---

## Docker Production

**Recommended** for most deployments. Uses Docker Compose to orchestrate all services.

### 1. System Requirements

- Docker 20.10+
- Docker Compose 2.0+
- 2GB RAM minimum (4GB recommended)
- 10GB disk space minimum
- SSL certificate (for HTTPS)

### 2. Clone and Configure

```bash
# Clone repository
git clone <repository-url> /opt/PropManager
cd /opt/PropManager

# Copy environment template
cp .env.docker.example .env.docker

# CRITICAL: Edit .env.docker with production values
nano .env.docker
```

**Required environment variables:**

```bash
# Site configuration
SITE_URL=https://yourdomain.com
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DEBUG=False

# Security
SECRET_KEY=<generate-with-command-below>
POSTGRES_PASSWORD=<strong-random-password>

# Email (SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Optional: Payment gateways, Twilio, Weather API, etc.
# See .env.docker.example for complete list
```

**Generate SECRET_KEY:**

```bash
docker run --rm python:3.12-slim python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 3. SSL Certificates

**Option A: Let's Encrypt (Recommended)**

```bash
# Install certbot
sudo apt install certbot

# Generate certificates
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy to docker/nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem docker/nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem docker/nginx/ssl/

# Set permissions
sudo chmod 644 docker/nginx/ssl/*.pem
```

**Option B: Existing Certificates**

Place your SSL certificates in `docker/nginx/ssl/`:
- `fullchain.pem` - Certificate + intermediate chain
- `privkey.pem` - Private key

**Option C: Self-Signed (Development Only)**

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout docker/nginx/ssl/privkey.pem \
  -out docker/nginx/ssl/fullchain.pem \
  -subj "/CN=yourdomain.com"
```

### 4. Deploy Application

```bash
# Start all services with nginx
docker compose -f docker-compose.yml -f docker-compose.nginx.yml up -d --build

# Wait for services to start (check with: docker compose ps)

# Run migrations
docker compose exec web python manage.py migrate

# Collect static files
docker compose exec web python manage.py collectstatic --no-input

# Access setup wizard
# Visit https://yourdomain.com/setup/ to complete configuration
```

### 5. Verify Deployment

```bash
# Check service status
docker compose ps

# All services should show "running":
# - propmanager-db
# - propmanager-redis
# - propmanager-web
# - propmanager-worker
# - propmanager-nginx

# View logs
docker compose logs -f web

# Check task queue
docker compose exec web python manage.py qinfo
```

### 6. Setup Wizard

1. Visit `https://yourdomain.com/setup/`
2. Complete the 8-step wizard:
   - Welcome
   - Admin Account (create your admin user)
   - Database (auto-verified)
   - Communications (email/SMS)
   - Payment Gateway (configure at least one)
   - Integrations (AI, Weather, Rewards - optional)
   - Data Import (CSV or demo data - optional)
   - Review & Complete
3. Access admin portal at `https://yourdomain.com/admin-portal/`

### 7. SSL Auto-Renewal (Let's Encrypt)

```bash
# Add renewal hook to copy new certificates
sudo nano /etc/letsencrypt/renewal-hooks/deploy/propmanager.sh
```

Contents:

```bash
#!/bin/bash
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /opt/PropManager/docker/nginx/ssl/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /opt/PropManager/docker/nginx/ssl/
chmod 644 /opt/PropManager/docker/nginx/ssl/*.pem
docker compose -f /opt/PropManager/docker-compose.yml -f /opt/PropManager/docker-compose.nginx.yml restart nginx
```

```bash
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/propmanager.sh

# Test renewal
sudo certbot renew --dry-run
```

### 8. Backups

**Database Backup:**

```bash
# Backup script: /opt/PropManager/backup.sh
#!/bin/bash
BACKUP_DIR="/backups/propmanager"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# PostgreSQL backup
docker compose exec -T db pg_dump -U propmanager propmanager | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Media files backup
tar -czf $BACKUP_DIR/media_$DATE.tar.gz media/

# Keep last 30 days
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
chmod +x /opt/PropManager/backup.sh

# Add to cron (daily at 2am)
crontab -e
# Add: 0 2 * * * /opt/PropManager/backup.sh >> /var/log/propmanager_backup.log 2>&1
```

**Restore from Backup:**

```bash
# Stop services
docker compose down

# Restore database
gunzip -c /backups/propmanager/db_20260221_020000.sql.gz | \
  docker compose exec -T db psql -U propmanager propmanager

# Restore media files
tar -xzf /backups/propmanager/media_20260221_020000.tar.gz

# Restart services
docker compose -f docker-compose.yml -f docker-compose.nginx.yml up -d
```

### 9. Monitoring

**View Logs:**

```bash
# Web application
docker compose logs -f web

# Background worker
docker compose logs -f worker

# Nginx access/error logs
docker compose logs -f nginx

# Database
docker compose logs -f db

# All services
docker compose logs -f
```

**Health Checks:**

```bash
# Application health
curl https://yourdomain.com/health/

# Liveness check
curl https://yourdomain.com/live/

# Readiness check
curl https://yourdomain.com/ready/
```

**Resource Usage:**

```bash
# Container stats
docker stats

# Disk usage
docker system df
```

### 10. Updating

```bash
cd /opt/PropManager
git pull origin master

# Rebuild and restart
docker compose -f docker-compose.yml -f docker-compose.nginx.yml up -d --build

# Run migrations
docker compose exec web python manage.py migrate

# Collect static files
docker compose exec web python manage.py collectstatic --no-input

# Verify
docker compose ps
```

### 11. Troubleshooting

**Services won't start:**

```bash
# Check logs
docker compose logs

# Check specific service
docker compose logs db
docker compose logs web

# Restart specific service
docker compose restart web
```

**Database connection errors:**

```bash
# Verify DATABASE_URL in .env.docker
# Default: postgres://propmanager:<POSTGRES_PASSWORD>@db:5432/propmanager

# Check PostgreSQL is ready
docker compose exec db pg_isready -U propmanager
```

**Permission errors:**

```bash
# Fix media directory permissions
sudo chown -R 1000:1000 media/

# Fix static files
sudo chown -R 1000:1000 staticfiles/
```

**Out of disk space:**

```bash
# Clean up Docker
docker system prune -a

# Clean old images
docker image prune -a

# Check disk usage
df -h
du -sh media/ staticfiles/
```

---

## Traditional Deployment

For deployments without Docker, using systemd and Gunicorn.

### 1. System Requirements

- Python 3.10+
- PostgreSQL 14+
- Nginx (recommended reverse proxy)
- systemd (for process management)

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
