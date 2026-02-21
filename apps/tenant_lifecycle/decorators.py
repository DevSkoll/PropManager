"""
Decorators for tenant onboarding views.
"""

from functools import wraps

from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import OnboardingSession


def onboarding_token_required(view_func):
    """
    Decorator for views that require a valid onboarding token.

    - Validates the token exists and is not expired
    - Marks first_accessed_at on first visit
    - Updates status from 'invited' to 'started'
    - Attaches session to request as request.onboarding_session
    - Returns 404 for invalid/expired/cancelled sessions

    Usage:
        @onboarding_token_required
        def my_view(request, token):
            session = request.onboarding_session
            ...
    """
    @wraps(view_func)
    def wrapper(request, token, *args, **kwargs):
        try:
            session = OnboardingSession.objects.select_related(
                "template", "unit", "lease", "tenant"
            ).get(access_token=token)
        except OnboardingSession.DoesNotExist:
            raise Http404("Invalid onboarding link.")

        # Check if cancelled
        if session.status == "cancelled":
            return render(request, "tenant_lifecycle/onboarding/cancelled.html", {
                "session": session,
            })

        # Check if already completed
        if session.status == "completed":
            return render(request, "tenant_lifecycle/onboarding/already_complete.html", {
                "session": session,
            })

        # Check if expired
        if session.is_expired:
            session.status = "expired"
            session.save(update_fields=["status", "updated_at"])
            return render(request, "tenant_lifecycle/onboarding/expired.html", {
                "session": session,
            })

        # Mark first access
        if not session.first_accessed_at:
            session.first_accessed_at = timezone.now()
            session.status = "started"
            session.save(update_fields=["first_accessed_at", "status", "updated_at"])

        # Attach session to request
        request.onboarding_session = session

        return view_func(request, token, *args, **kwargs)

    return wrapper


def onboarding_step_required(step_name):
    """
    Decorator to ensure a specific onboarding step is being accessed appropriately.

    Checks that:
    - Previous required steps are completed
    - The step is enabled in the template

    Usage:
        @onboarding_token_required
        @onboarding_step_required("personal_info")
        def personal_info_view(request, token):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, token, *args, **kwargs):
            session = getattr(request, "onboarding_session", None)
            if not session:
                raise Http404("Session not found.")

            template = session.template
            if not template:
                raise Http404("Template not found.")

            # Check if step is enabled
            steps_config = template.steps_config
            step_config = steps_config.get(step_name, {})

            if not step_config.get("enabled", True):
                # Step disabled, skip to next
                return redirect("tenant_lifecycle:onboarding_router", token=token)

            # Check if previous required steps are completed
            enabled_steps = template.get_enabled_steps()
            for step in enabled_steps:
                if step["name"] == step_name:
                    break
                if step["required"] and step["name"] not in session.steps_completed:
                    # Must complete previous required step first
                    return redirect(
                        f"tenant_lifecycle:onboarding_{step['name']}",
                        token=token
                    )

            return view_func(request, token, *args, **kwargs)

        return wrapper
    return decorator


def get_client_ip(request) -> str:
    """Get client IP address from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def log_step_access(session, step_name, request):
    """
    Log access to an onboarding step.

    Creates or updates an OnboardingStepLog entry.
    """
    from .models import OnboardingStepLog

    # Get attempt number
    existing_attempts = OnboardingStepLog.objects.filter(
        session=session,
        step_name=step_name,
    ).count()

    OnboardingStepLog.objects.create(
        session=session,
        step_name=step_name,
        attempt_number=existing_attempts + 1,
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
    )
