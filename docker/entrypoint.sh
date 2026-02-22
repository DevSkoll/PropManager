#!/bin/bash
# ============================================
# PropManager Container Entrypoint
# Handles startup tasks: wait for services, migrations, static files
# ============================================

set -e

echo "============================================"
echo "PropManager Container Startup"
echo "============================================"
echo "Settings: ${DJANGO_SETTINGS_MODULE}"
echo "Command: $@"
echo "============================================"

# ============================================
# Wait for PostgreSQL
# ============================================
echo "Waiting for PostgreSQL..."
MAX_RETRIES=30
RETRY_COUNT=0

until python -c "
import os
import psycopg
try:
    psycopg.connect(os.environ['DATABASE_URL'])
    exit(0)
except Exception as e:
    print(f'  Waiting for database... ({e})')
    exit(1)
" 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "ERROR: Failed to connect to PostgreSQL after $MAX_RETRIES attempts"
        exit 1
    fi
    sleep 2
done
echo "PostgreSQL is ready!"

# ============================================
# Wait for Redis (if configured)
# ============================================
if [ -n "$REDIS_URL" ]; then
    echo "Waiting for Redis..."
    RETRY_COUNT=0

    until python -c "
import redis
import os
try:
    r = redis.from_url(os.environ['REDIS_URL'])
    r.ping()
    exit(0)
except Exception as e:
    print(f'  Waiting for Redis... ({e})')
    exit(1)
" 2>/dev/null; do
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
            echo "ERROR: Failed to connect to Redis after $MAX_RETRIES attempts"
            exit 1
        fi
        sleep 1
    done
    echo "Redis is ready!"
fi

# ============================================
# Run migrations (skip for worker processes)
# ============================================
if [[ "$1" != *"qcluster"* ]] && [[ "$1" != *"celery"* ]]; then
    echo "Running database migrations..."
    python manage.py migrate --noinput

    # Collect static files (production only)
    if [ "$DJANGO_SETTINGS_MODULE" = "config.settings.production" ]; then
        echo "Collecting static files..."
        python manage.py collectstatic --noinput --clear
    fi
fi

# ============================================
# Execute the main command
# ============================================
echo "============================================"
echo "Starting: $@"
echo "============================================"
exec "$@"
