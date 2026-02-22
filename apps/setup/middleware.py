from django.shortcuts import redirect


class SetupRequiredMiddleware:
    """
    Redirects all requests to /setup/ if setup is not complete.

    Allows access to:
    - /setup/* (setup wizard itself)
    - /health/, /live/, /ready/ (health checks)
    - /static/*, /media/* (static files)
    - /django-admin/ (for recovery)
    """

    EXEMPT_PATHS = [
        "/setup/",
        "/health/",
        "/live/",
        "/ready/",
        "/static/",
        "/media/",
        "/django-admin/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response
        self._setup_checked = False
        self._setup_complete = None

    def __call__(self, request):
        # Skip check for exempt paths
        if any(request.path.startswith(p) for p in self.EXEMPT_PATHS):
            return self.get_response(request)

        # Check if setup is required
        if not self._is_setup_complete():
            return redirect("setup:welcome")

        return self.get_response(request)

    def _is_setup_complete(self):
        """
        Check if setup has been completed.
        Caches the result to avoid repeated database queries.
        """
        # Return cached value if we've already checked and setup is complete
        if self._setup_complete:
            return True

        try:
            from apps.setup.models import SetupConfiguration

            self._setup_complete = SetupConfiguration.is_setup_complete()
            return self._setup_complete
        except Exception:
            # Database not ready, model not migrated, or other error
            # Allow request to proceed to avoid blocking during initial setup
            return True
