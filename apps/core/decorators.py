from functools import wraps

from django.http import Http404, HttpResponseForbidden
from django.shortcuts import redirect


def tenant_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/tenant/login/?next={request.path}")
        if request.user.role != "tenant":
            return HttpResponseForbidden("Access denied.")
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/admin-portal/login/?next={request.path}")
        if request.user.role not in ("admin", "staff"):
            return HttpResponseForbidden("Access denied.")
        return view_func(request, *args, **kwargs)
    return wrapper


def contractor_token_required(view_func):
    @wraps(view_func)
    def wrapper(request, token, *args, **kwargs):
        from django.utils import timezone
        from apps.accounts.models import ContractorAccessToken

        try:
            access_token = ContractorAccessToken.objects.select_related("work_order").get(
                token=token,
                is_revoked=False,
                expires_at__gt=timezone.now(),
            )
        except ContractorAccessToken.DoesNotExist:
            raise Http404("Invalid or expired access link.")

        access_token.last_accessed_at = timezone.now()
        access_token.save(update_fields=["last_accessed_at"])
        request.contractor_token = access_token
        return view_func(request, token, *args, **kwargs)
    return wrapper
