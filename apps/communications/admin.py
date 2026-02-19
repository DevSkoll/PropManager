from django.contrib import admin

from .models import Announcement, Message, MessageThread, Notification


@admin.register(MessageThread)
class MessageThreadAdmin(admin.ModelAdmin):
    list_display = ("subject", "is_closed", "created_at")
    list_filter = ("is_closed",)
    search_fields = ("subject",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("thread", "sender", "is_read", "created_at")
    list_filter = ("is_read",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "recipient", "channel", "category", "is_read", "created_at")
    list_filter = ("channel", "category", "is_read")
    search_fields = ("title", "recipient__username")


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "property", "is_published", "published_at")
    list_filter = ("is_published",)
    search_fields = ("title",)
