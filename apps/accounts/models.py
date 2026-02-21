import secrets
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.core.validators import validate_phone_number


class User(AbstractUser):
    ROLE_CHOICES = [
        ("tenant", "Tenant"),
        ("admin", "Admin"),
        ("staff", "Staff"),
    ]
    CONTACT_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="tenant", db_index=True)
    phone_number = models.CharField(
        max_length=20, blank=True, default="", validators=[validate_phone_number]
    )
    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    preferred_contact = models.CharField(
        max_length=5, choices=CONTACT_CHOICES, default="email"
    )

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_tenant(self):
        return self.role == "tenant"

    @property
    def is_admin_user(self):
        return self.role in ("admin", "staff")


class TenantProfile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tenant_profile"
    )

    # Personal identification (collected during onboarding)
    date_of_birth = models.DateField(null=True, blank=True)
    ssn_last_four = models.CharField(
        max_length=4, blank=True, default="",
        help_text="Last 4 digits of SSN for verification purposes."
    )
    drivers_license_state = models.CharField(max_length=2, blank=True, default="")
    drivers_license_number = models.CharField(max_length=50, blank=True, default="")

    # Emergency contact (legacy - now using TenantEmergencyContact)
    emergency_contact_name = models.CharField(max_length=200, blank=True, default="")
    emergency_contact_phone = models.CharField(
        max_length=20, blank=True, default="", validators=[validate_phone_number]
    )

    move_in_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Tenant Profile: {self.user}"


class AdminProfile(TimeStampedModel):
    OTP_DELIVERY_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="admin_profile"
    )
    otp_enabled = models.BooleanField(default=False)
    otp_delivery = models.CharField(
        max_length=5, choices=OTP_DELIVERY_CHOICES, default="email"
    )

    def __str__(self):
        return f"Admin Profile: {self.user}"


class OTPToken(TimeStampedModel):
    PURPOSE_CHOICES = [
        ("login", "Login"),
        ("2fa", "Two-Factor Auth"),
    ]
    DELIVERY_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="otp_tokens"
    )
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=5, choices=PURPOSE_CHOICES)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    delivery_method = models.CharField(max_length=5, choices=DELIVERY_CHOICES, default="email")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"OTP for {self.user} ({self.purpose})"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired

    @classmethod
    def generate(cls, user, purpose="login", delivery_method="email"):
        if settings.DEBUG:
            code = getattr(settings, "DEV_OTP_CODE", "123456")
        else:
            import random
            code = "".join([str(random.randint(0, 9)) for _ in range(settings.OTP_LENGTH)])
        expires_at = timezone.now() + timezone.timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        # Invalidate existing unused tokens for this user/purpose
        cls.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)
        return cls.objects.create(
            user=user,
            code=code,
            purpose=purpose,
            expires_at=expires_at,
            delivery_method=delivery_method,
        )


class ContractorAccessToken(TimeStampedModel):
    token = models.CharField(max_length=64, unique=True, db_index=True)
    contractor_name = models.CharField(max_length=200)
    contractor_phone = models.CharField(
        max_length=20, blank=True, default="", validators=[validate_phone_number]
    )
    contractor_email = models.EmailField(blank=True, default="")
    work_order = models.ForeignKey(
        "workorders.WorkOrder", on_delete=models.CASCADE, related_name="access_tokens"
    )
    expires_at = models.DateTimeField()
    is_revoked = models.BooleanField(default=False)
    last_accessed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Token for {self.contractor_name} - WO#{self.work_order_id}"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_valid(self):
        return not self.is_revoked and not self.is_expired

    @classmethod
    def generate_token(cls):
        return secrets.token_urlsafe(48)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()
        super().save(*args, **kwargs)
