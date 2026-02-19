from django.contrib import admin

from .models import (
    EmailConfig,
    EventTypeSubscription,
    GroupContact,
    NotificationGroup,
    NotificationLog,
    ReminderLog,
    SMSConfig,
    TenantNotificationPreference,
)


class GroupContactInline(admin.TabularInline):
    model = GroupContact
    extra = 0


class EventTypeSubscriptionInline(admin.TabularInline):
    model = EventTypeSubscription
    extra = 0


@admin.register(NotificationGroup)
class NotificationGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    inlines = [GroupContactInline, EventTypeSubscriptionInline]


@admin.register(GroupContact)
class GroupContactAdmin(admin.ModelAdmin):
    list_display = ("display_name", "group", "channel", "is_active")
    list_filter = ("channel", "is_active")
    search_fields = ("external_name", "user__username", "user__first_name", "user__last_name")


@admin.register(EventTypeSubscription)
class EventTypeSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("group", "event_type", "created_at")
    list_filter = ("event_type",)


@admin.register(TenantNotificationPreference)
class TenantNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("tenant", "category", "channel")
    list_filter = ("category", "channel")
    search_fields = ("tenant__username", "tenant__first_name", "tenant__last_name")


@admin.register(ReminderLog)
class ReminderLogAdmin(admin.ModelAdmin):
    list_display = ("invoice", "sent_by", "channel", "sent_at")
    list_filter = ("channel",)
    search_fields = ("invoice__invoice_number",)
    readonly_fields = ("sent_at",)


@admin.register(EmailConfig)
class EmailConfigAdmin(admin.ModelAdmin):
    list_display = ("display_name", "email_host", "default_from_email", "is_active", "last_test_success", "created_at")
    list_filter = ("is_active", "last_test_success")


@admin.register(SMSConfig)
class SMSConfigAdmin(admin.ModelAdmin):
    list_display = ("display_name", "provider", "phone_number", "is_active", "last_test_success", "created_at")
    list_filter = ("is_active", "provider", "last_test_success")


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("channel", "status", "recipient", "subject", "source", "created_at")
    list_filter = ("channel", "status", "source")
    search_fields = ("recipient", "subject")
    readonly_fields = ("channel", "status", "recipient", "subject", "body_preview", "error_message", "source")
