from .base import *  # noqa: F401, F403

DEBUG = True

# ============================================
# Database Configuration
# Support both SQLite (local) and PostgreSQL (Docker)
# ============================================
if env("DATABASE_URL", default=None):
    # Use PostgreSQL when DATABASE_URL is set (Docker development)
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    # Fall back to SQLite for local development
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ============================================
# Email Configuration
# ============================================
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ============================================
# Development Convenience Settings
# ============================================
# Default OTP code for development (skip checking console for codes)
DEV_OTP_CODE = env("DEV_OTP_CODE", default="123456")

# WhiteNoise in dev serves files without collectstatic
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# ============================================
# Debug Toolbar (if installed)
# ============================================
try:
    import debug_toolbar  # noqa: F401

    INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
    INTERNAL_IPS = ["127.0.0.1", "localhost"]
    # Allow debug toolbar in Docker
    import socket

    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS += [".".join(ip.split(".")[:-1] + ["1"]) for ip in ips]
except ImportError:
    pass
