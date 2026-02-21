"""
Django admin registration for AI Gateway models.
"""

from django.contrib import admin

from .models import AICapability, AIProvider


@admin.register(AIProvider)
class AIProviderAdmin(admin.ModelAdmin):
    list_display = ["name", "provider", "is_active", "is_default", "created_at"]
    list_filter = ["provider", "is_active", "is_default"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-is_default", "-is_active", "name"]


@admin.register(AICapability)
class AICapabilityAdmin(admin.ModelAdmin):
    list_display = ["capability", "is_enabled", "provider", "created_at"]
    list_filter = ["is_enabled", "capability"]
    readonly_fields = ["created_at", "updated_at"]
