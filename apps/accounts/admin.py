from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AdminProfile, ContractorAccessToken, OTPToken, TenantProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "is_active")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name", "phone_number")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Property Manager", {
            "fields": ("role", "phone_number", "is_phone_verified", "is_email_verified", "preferred_contact"),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Property Manager", {
            "fields": ("role", "email", "first_name", "last_name", "phone_number"),
        }),
    )


@admin.register(TenantProfile)
class TenantProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "emergency_contact_name", "move_in_date")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "otp_enabled", "otp_delivery")


@admin.register(OTPToken)
class OTPTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "purpose", "delivery_method", "is_used", "expires_at", "created_at")
    list_filter = ("purpose", "delivery_method", "is_used")
    readonly_fields = ("code",)


@admin.register(ContractorAccessToken)
class ContractorAccessTokenAdmin(admin.ModelAdmin):
    list_display = ("contractor_name", "work_order", "is_revoked", "expires_at", "last_accessed_at")
    list_filter = ("is_revoked",)
    search_fields = ("contractor_name", "contractor_email")
