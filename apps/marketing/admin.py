from django.contrib import admin

from .models import Campaign, CampaignLink, CampaignRecipient, CampaignSegment


class CampaignSegmentInline(admin.TabularInline):
    model = CampaignSegment
    extra = 0


class CampaignRecipientInline(admin.TabularInline):
    model = CampaignRecipient
    extra = 0


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "status", "scheduled_at", "sent_at")
    list_filter = ("status",)
    search_fields = ("name", "subject")
    inlines = [CampaignSegmentInline]


@admin.register(CampaignRecipient)
class CampaignRecipientAdmin(admin.ModelAdmin):
    list_display = ("campaign", "email", "status", "sent_at", "opened_at")
    list_filter = ("status",)


@admin.register(CampaignLink)
class CampaignLinkAdmin(admin.ModelAdmin):
    list_display = ("campaign", "original_url", "click_count")
