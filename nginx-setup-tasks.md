# PropManager Nginx Configuration Tasks

## Current Status
✅ PropManager is running on localhost:8001
✅ Seed data loaded (17 users, 5 properties, 15 active leases, 119 invoices)
✅ All containers healthy (web, worker, db, redis)

## Domain Setup Tasks

### 1. DNS Configuration
- [ ] Ensure propdemo.arctek.us DNS A record points to your server IP
- [ ] Verify DNS propagation: `nslookup propdemo.arctek.us`

### 2. Nginx Configuration
Create nginx configuration file at `/etc/nginx/sites-available/propdemo.arctek.us` or your Unraid nginx config location:

```nginx
upstream propmanager_backend {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name propdemo.arctek.us;

    # Optional: Redirect to HTTPS (after SSL setup)
    # return 301 https://$server_name$request_uri;

    client_max_body_size 100M;

    # Logs
    access_log /var/log/nginx/propdemo.arctek.us.access.log;
    error_log /var/log/nginx/propdemo.arctek.us.error.log;

    # Static files (served by Django in dev mode)
    location /static/ {
        proxy_pass http://propmanager_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Media files (served by Django in dev mode)
    location /media/ {
        proxy_pass http://propmanager_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Main application
    location / {
        proxy_pass http://propmanager_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### 3. Enable Nginx Site
- [ ] Create/update nginx configuration file
- [ ] Enable site: `ln -s /etc/nginx/sites-available/propdemo.arctek.us /etc/nginx/sites-enabled/` (if using sites-available/enabled pattern)
- [ ] Test configuration: `nginx -t`
- [ ] Reload nginx: `systemctl reload nginx` or `nginx -s reload`

### 4. Django Settings Update (Optional for Production)
Update Django's ALLOWED_HOSTS to include the domain:
- [ ] Add `propdemo.arctek.us` to allowed hosts in development settings or use environment variable

Current development settings already have `DEBUG=True` which is permissive, but for better security:
```bash
docker exec propmanager-web-dev python manage.py shell -c "
from django.conf import settings
print('ALLOWED_HOSTS:', settings.ALLOWED_HOSTS)
"
```

### 5. SSL/HTTPS Setup (Optional but Recommended)
If you want HTTPS:
- [ ] Install certbot: `apt-get install certbot python3-certbot-nginx` (or use your Unraid method)
- [ ] Obtain certificate: `certbot --nginx -d propdemo.arctek.us`
- [ ] Certbot will automatically update nginx configuration for HTTPS

### 6. Testing
- [ ] Access http://propdemo.arctek.us (or https if SSL configured)
- [ ] Test admin portal: http://propdemo.arctek.us/admin-portal/login/
- [ ] Test tenant portal: http://propdemo.arctek.us/tenant/login/

## Test Accounts (From Seed Data)

### Admin Portal (`/admin-portal/login/`)
- **Username:** admin / **Password:** admin123 (Admin role)
- **Username:** staff / **Password:** staff123 (Staff role)

### Tenant Portal (`/tenant/login/`)
Use any of these tenant usernames with password `tenant123`:
- `perfect_payer` - Perfect payment history
- `model_tenant` - Model tenant
- `reliable_renter` - Reliable payer
- `chronic_charlie` - Chronic late payer
- `overdue_olivia` - Has overdue balance
- ...and 10 more test tenants

**Note:** In development mode, OTP code is always `123456`

### Django Admin (`/django-admin/`)
- **Username:** admin / **Password:** admin123

## Application Info
- **Container:** propmanager-web-dev
- **Internal Port:** 8000
- **External Port:** 8001
- **Database:** PostgreSQL (port 5433)
- **Redis:** port 6380
- **Docker Compose Files:** 
  - `docker-compose.yml`
  - `docker-compose.dev.override.yml`

## Useful Commands

### View Logs
```bash
docker logs -f propmanager-web-dev
docker logs -f propmanager-worker-dev
```

### Restart Containers
```bash
WEB_PORT=8001 docker compose -f docker-compose.yml -f docker-compose.dev.override.yml restart
```

### Stop Application
```bash
WEB_PORT=8001 docker compose -f docker-compose.yml -f docker-compose.dev.override.yml down
```

### Start Application
```bash
WEB_PORT=8001 docker compose -f docker-compose.yml -f docker-compose.dev.override.yml up -d
```

### Access Django Shell
```bash
docker exec -it propmanager-web-dev python manage.py shell
```

## Notes
- Development mode has hot-reload enabled
- DEBUG mode is ON - do not use for production
- Secret key is hardcoded for development
- Database and media files are persisted in Docker volumes
