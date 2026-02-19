from django.http import HttpResponseForbidden
from django.shortcuts import redirect


class RoleBasedAccessMiddleware:
    """Restrict tenant portal to tenants, admin portal to admins/staff."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if path.startswith("/tenant/") and path not in ("/tenant/login/", "/tenant/login/verify/"):
            if request.user.is_authenticated and request.user.role not in ("tenant",):
                return HttpResponseForbidden("Access denied.")
            if not request.user.is_authenticated:
                return redirect(f"/tenant/login/?next={path}")

        if path.startswith("/admin-portal/") and path not in (
            "/admin-portal/login/",
            "/admin-portal/login/verify/",
        ):
            if request.user.is_authenticated and request.user.role not in ("admin", "staff"):
                return HttpResponseForbidden("Access denied.")
            if not request.user.is_authenticated:
                return redirect(f"/admin-portal/login/?next={path}")

        return self.get_response(request)
