# ============================================
# PropManager Docker Build
# Multi-stage build for production and development
# ============================================

# Python version - use 3.12 for better dependency compatibility
ARG PYTHON_VERSION=3.12

# ============================================
# Stage 1: Builder
# Install dependencies in a separate stage for caching
# ============================================
FROM python:${PYTHON_VERSION}-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements/base.txt requirements/base.txt
COPY requirements/prod.txt requirements/prod.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements/prod.txt

# ============================================
# Stage 2: Production
# Minimal runtime image
# ============================================
FROM python:${PYTHON_VERSION}-slim AS production

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libxml2 \
    libxslt1.1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash --uid 1000 appuser

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories
RUN mkdir -p staticfiles media logs \
    && chown -R appuser:appuser staticfiles media logs \
    && chmod +x docker/entrypoint.sh

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

# Switch to non-root user
USER appuser

EXPOSE 8000

ENTRYPOINT ["./docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--worker-class", "gthread", "--worker-tmp-dir", "/dev/shm"]

# ============================================
# Stage 3: Development
# Full development environment with hot reload
# ============================================
FROM python:${PYTHON_VERSION}-slim AS development

WORKDIR /app

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    curl \
    git \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements/ requirements/

# Install all dependencies including dev
RUN pip install --no-cache-dir \
    -r requirements/base.txt \
    -r requirements/dev.txt \
    -r requirements/prod.txt

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.development

EXPOSE 8000

# Default command - can be overridden in docker-compose
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
