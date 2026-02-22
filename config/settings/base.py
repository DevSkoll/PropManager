import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CSRF_TRUSTED_ORIGINS=(list, []),
)
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))


# ============================================
# Docker Secrets Support
# ============================================
def get_secret(secret_name, default=None):
    """
    Read secret from Docker secrets or fall back to environment variable.

    Docker secrets are mounted at /run/secrets/<secret_name> in containers.
    This allows secure secret management in Docker Swarm deployments.
    """
    secret_path = f"/run/secrets/{secret_name}"
    if os.path.exists(secret_path):
        with open(secret_path) as f:
            return f.read().strip()
    # Fall back to environment variable (uppercase with underscores)
    env_key = secret_name.upper().replace("-", "_")
    return os.environ.get(env_key, default)


# ============================================
# Core Django Settings
# ============================================
SECRET_KEY = get_secret("django_secret_key", env("SECRET_KEY", default="insecure-dev-key-change-in-production"))
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# Site URL - the public URL where the app is accessible
# Used for generating links in emails, signing workflows, etc.
SITE_URL = env("SITE_URL", default="http://localhost:8000")

# Build CSRF_TRUSTED_ORIGINS from SITE_URL and optional env var
_csrf_origins = env("CSRF_TRUSTED_ORIGINS", default=[])
if SITE_URL and SITE_URL not in _csrf_origins:
    _csrf_origins.insert(0, SITE_URL)
CSRF_TRUSTED_ORIGINS = _csrf_origins

AUTH_USER_MODEL = "accounts.User"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Third party
    "django_htmx",
    "crispy_forms",
    "crispy_bootstrap5",
    "django_q",
    # Local apps
    "apps.core",
    "apps.accounts",
    "apps.properties",
    "apps.leases",
    "apps.billing",
    "apps.rewards",
    "apps.workorders",
    "apps.communications",
    "apps.documents",
    "apps.weather",
    "apps.marketing",
    "apps.notifications",
    "apps.tenant_lifecycle",
    "apps.ai",
    "apps.setup",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "apps.setup.middleware.SetupRequiredMiddleware",
    "apps.core.middleware.RoleBasedAccessMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.app_launcher_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.PasswordlessOTPBackend",
    "django.contrib.auth.backends.ModelBackend",
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ============================================
# Redis Configuration (optional)
# ============================================
REDIS_URL = env("REDIS_URL", default=None)

if REDIS_URL:
    # Use django-redis for caching (provides more features than Django's built-in)
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
        }
    }
    # Use Redis for sessions (faster than database)
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
else:
    # Default to database cache when Redis not available
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "django_cache",
        }
    }

# ============================================
# Django-Q2 Task Queue
# ============================================
Q_CLUSTER = {
    "name": "propmanager",
    "workers": env.int("Q_WORKERS", default=2),
    "recycle": 500,
    "timeout": 120,
    "retry": 180,
    "queue_limit": 50,
    "bulk": 10,
}

# Use Redis broker when available, otherwise fall back to ORM
if REDIS_URL:
    Q_CLUSTER["redis"] = REDIS_URL
else:
    Q_CLUSTER["orm"] = "default"

# Email
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@propmanager.com")

# Twilio
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN", default="")
TWILIO_PHONE_NUMBER = env("TWILIO_PHONE_NUMBER", default="")

# OpenWeatherMap
OPENWEATHERMAP_API_KEY = env("OPENWEATHERMAP_API_KEY", default="")

# OTP Settings
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10
OTP_MAX_REQUESTS_PER_HOUR = 5

# Login URLs
LOGIN_URL = "/tenant/login/"
LOGIN_REDIRECT_URL = "/tenant/dashboard/"
LOGOUT_REDIRECT_URL = "/"

# Document uploads
DOCUMENT_MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
