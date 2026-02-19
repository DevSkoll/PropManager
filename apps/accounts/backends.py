from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend

User = get_user_model()


class PasswordlessOTPBackend(BaseBackend):
    """Authenticate tenants via OTP code (passwordless login)."""

    def authenticate(self, request, user_id=None, otp_code=None, **kwargs):
        if user_id is None or otp_code is None:
            return None

        from apps.accounts.models import OTPToken

        try:
            user = User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return None

        token = OTPToken.objects.filter(
            user=user,
            code=otp_code,
            is_used=False,
        ).order_by("-created_at").first()

        if token and token.is_valid:
            token.is_used = True
            token.save(update_fields=["is_used"])
            return user

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
