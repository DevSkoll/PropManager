"""URL utilities for generating absolute URLs."""

from django.conf import settings
from django.urls import reverse


def get_absolute_url(path_or_view_name, *args, **kwargs):
    """
    Build absolute URL from path or view name.

    Uses the SITE_URL setting to construct full URLs for use in
    emails, notifications, and other external communications.

    Args:
        path_or_view_name: Either a URL path (e.g., "/tenant/dashboard/")
                          or a view name (e.g., "leases_signing:signing_page")
        *args: Positional arguments for reverse() if using view name
        **kwargs: Keyword arguments for reverse() if using view name

    Returns:
        Full absolute URL string

    Usage:
        # With path
        get_absolute_url("/tenant/dashboard/")
        # -> "https://propmanager.arctek.us/tenant/dashboard/"

        # With view name and kwargs
        get_absolute_url("leases_signing:signing_page", token="abc123")
        # -> "https://propmanager.arctek.us/sign/abc123/"

        # With view name and args
        get_absolute_url("tenant_lease_detail", 42)
        # -> "https://propmanager.arctek.us/tenant/leases/42/"
    """
    site_url = settings.SITE_URL.rstrip("/")

    # If it looks like a URL name (contains colon or no leading slash)
    if ":" in path_or_view_name or not path_or_view_name.startswith("/"):
        path = reverse(path_or_view_name, args=args, kwargs=kwargs)
    else:
        path = path_or_view_name

    return f"{site_url}{path}"
