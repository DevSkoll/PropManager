import base64

from django.contrib import messages
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.core.decorators import admin_required
from apps.leases.models import Lease

from .forms import CampaignForm, CampaignSegmentFormSet
from .models import Campaign, CampaignLink, CampaignRecipient


# ---------------------------------------------------------------------------
# Transparent 1x1 GIF (43 bytes)
# ---------------------------------------------------------------------------
TRACKING_PIXEL_GIF = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


# ===========================================================================
# Segment Resolution Helper
# ===========================================================================


def resolve_segments(campaign):
    """Resolve campaign segments to a set of tenant User objects."""
    tenant_ids = set()

    for segment in campaign.segments.all():
        filter_type = segment.filter_type
        filter_value = segment.filter_value or {}

        if filter_type == "all":
            qs = User.objects.filter(role="tenant", is_active=True)
            tenant_ids.update(qs.values_list("id", flat=True))

        elif filter_type == "by_property":
            property_id = filter_value.get("property_id")
            if property_id:
                lease_tenants = Lease.objects.filter(
                    unit__property_id=property_id, status="active"
                ).values_list("tenant_id", flat=True)
                tenant_ids.update(lease_tenants)

        elif filter_type == "by_lease_status":
            status = filter_value.get("status")
            if status:
                lease_tenants = Lease.objects.filter(
                    status=status
                ).values_list("tenant_id", flat=True)
                tenant_ids.update(lease_tenants)

        elif filter_type == "by_move_in_date":
            start = filter_value.get("start")
            end = filter_value.get("end")
            qs = User.objects.filter(role="tenant", is_active=True)
            if start:
                qs = qs.filter(tenant_profile__move_in_date__gte=start)
            if end:
                qs = qs.filter(tenant_profile__move_in_date__lte=end)
            tenant_ids.update(qs.values_list("id", flat=True))

    return User.objects.filter(id__in=tenant_ids, is_active=True)


# ===========================================================================
# Admin Views
# ===========================================================================


@admin_required
def campaign_list(request):
    """List all campaigns with optional status filter."""
    status_filter = request.GET.get("status", "")
    campaigns = Campaign.objects.all().order_by("-created_at")

    if status_filter:
        campaigns = campaigns.filter(status=status_filter)

    context = {
        "campaigns": campaigns,
        "status_filter": status_filter,
        "status_choices": Campaign.STATUS_CHOICES,
    }
    return render(request, "marketing/campaign_list.html", context)


@admin_required
def campaign_create(request):
    """Create a new campaign with segments."""
    if request.method == "POST":
        form = CampaignForm(request.POST)
        segment_formset = CampaignSegmentFormSet(request.POST, prefix="segments")

        if form.is_valid() and segment_formset.is_valid():
            campaign = form.save(commit=False)
            campaign.created_by = request.user
            campaign.save()

            segment_formset.instance = campaign
            segment_formset.save()

            messages.success(request, f'Campaign "{campaign.name}" created successfully.')
            return redirect("marketing_admin:campaign_detail", pk=campaign.pk)
    else:
        form = CampaignForm()
        segment_formset = CampaignSegmentFormSet(prefix="segments")

    context = {
        "form": form,
        "segment_formset": segment_formset,
    }
    return render(request, "marketing/campaign_create.html", context)


@admin_required
def campaign_detail(request, pk):
    """View campaign details with delivery statistics."""
    campaign = get_object_or_404(Campaign, pk=pk)
    recipients = campaign.recipients.select_related("tenant").all()

    total = recipients.count()
    sent = recipients.filter(status="sent").count()
    delivered = recipients.filter(status="delivered").count()
    opened = recipients.filter(status__in=["opened", "clicked"]).count()
    clicked = recipients.filter(status="clicked").count()
    bounced = recipients.filter(status="bounced").count()
    failed = recipients.filter(status="failed").count()

    # Denominators for rates: those that were actually sent/delivered
    rate_denominator = sent + delivered + opened + clicked
    open_rate = round((opened / rate_denominator) * 100, 1) if rate_denominator else 0
    click_rate = round((clicked / rate_denominator) * 100, 1) if rate_denominator else 0

    context = {
        "campaign": campaign,
        "recipients": recipients,
        "stats": {
            "total": total,
            "sent": sent,
            "delivered": delivered,
            "opened": opened,
            "clicked": clicked,
            "bounced": bounced,
            "failed": failed,
            "open_rate": open_rate,
            "click_rate": click_rate,
        },
    }
    return render(request, "marketing/campaign_detail.html", context)


@admin_required
def campaign_edit(request, pk):
    """Edit a draft campaign."""
    campaign = get_object_or_404(Campaign, pk=pk)

    if campaign.status != "draft":
        messages.error(request, "Only draft campaigns can be edited.")
        return redirect("marketing_admin:campaign_detail", pk=campaign.pk)

    if request.method == "POST":
        form = CampaignForm(request.POST, instance=campaign)
        segment_formset = CampaignSegmentFormSet(
            request.POST, instance=campaign, prefix="segments"
        )

        if form.is_valid() and segment_formset.is_valid():
            form.save()
            segment_formset.save()
            messages.success(request, f'Campaign "{campaign.name}" updated successfully.')
            return redirect("marketing_admin:campaign_detail", pk=campaign.pk)
    else:
        form = CampaignForm(instance=campaign)
        segment_formset = CampaignSegmentFormSet(instance=campaign, prefix="segments")

    context = {
        "form": form,
        "segment_formset": segment_formset,
        "campaign": campaign,
    }
    return render(request, "marketing/campaign_edit.html", context)


@admin_required
def campaign_preview(request, pk):
    """Preview campaign with recipient count based on segments."""
    campaign = get_object_or_404(Campaign, pk=pk)
    resolved_recipients = resolve_segments(campaign)
    recipient_count = resolved_recipients.count()

    context = {
        "campaign": campaign,
        "recipient_count": recipient_count,
        "recipients_preview": resolved_recipients[:20],
    }
    return render(request, "marketing/campaign_preview.html", context)


@admin_required
@require_POST
def campaign_send(request, pk):
    """Send or schedule a campaign."""
    campaign = get_object_or_404(Campaign, pk=pk)

    if campaign.status not in ("draft",):
        messages.error(request, "Only draft campaigns can be sent or scheduled.")
        return redirect("marketing_admin:campaign_detail", pk=campaign.pk)

    if campaign.scheduled_at and campaign.scheduled_at > timezone.now():
        campaign.status = "scheduled"
        campaign.save(update_fields=["status"])
        messages.success(
            request,
            f'Campaign "{campaign.name}" scheduled for {campaign.scheduled_at}.',
        )
    else:
        campaign.status = "sending"
        campaign.save(update_fields=["status"])
        # Dispatch async task via Django-Q2
        try:
            from django_q.tasks import async_task

            async_task("apps.marketing.tasks.send_campaign", str(campaign.pk))
        except ImportError:
            # Fallback: run synchronously if django-q is not available
            from .tasks import send_campaign

            send_campaign(str(campaign.pk))
        messages.success(request, f'Campaign "{campaign.name}" is now sending.')

    return redirect("marketing_admin:campaign_detail", pk=campaign.pk)


@admin_required
@require_POST
def campaign_cancel(request, pk):
    """Cancel a scheduled or sending campaign."""
    campaign = get_object_or_404(Campaign, pk=pk)

    if campaign.status not in ("scheduled", "sending"):
        messages.error(request, "Only scheduled or currently sending campaigns can be cancelled.")
        return redirect("marketing_admin:campaign_detail", pk=campaign.pk)

    campaign.status = "cancelled"
    campaign.save(update_fields=["status"])
    messages.success(request, f'Campaign "{campaign.name}" has been cancelled.')
    return redirect("marketing_admin:campaign_detail", pk=campaign.pk)


# ===========================================================================
# Tracking Views (no auth required -- triggered by email clients)
# ===========================================================================


def tracking_pixel(request, recipient_pk):
    """Record an email open via a 1x1 transparent tracking pixel."""
    try:
        recipient = CampaignRecipient.objects.get(pk=recipient_pk)
        if recipient.status in ("sent", "delivered"):
            recipient.status = "opened"
            recipient.opened_at = timezone.now()
            recipient.save(update_fields=["status", "opened_at"])
    except CampaignRecipient.DoesNotExist:
        pass

    return HttpResponse(TRACKING_PIXEL_GIF, content_type="image/gif")


def tracking_redirect(request, tracking_token):
    """Record a link click and redirect to the original URL."""
    link = get_object_or_404(CampaignLink, tracking_token=tracking_token)

    # Increment click count
    CampaignLink.objects.filter(pk=link.pk).update(click_count=F("click_count") + 1)

    # Try to update recipient status if we can identify them
    recipient_pk = request.GET.get("rid")
    if recipient_pk:
        try:
            recipient = CampaignRecipient.objects.get(pk=recipient_pk)
            if recipient.status in ("sent", "delivered", "opened"):
                recipient.status = "clicked"
                recipient.clicked_at = timezone.now()
                if not recipient.opened_at:
                    recipient.opened_at = timezone.now()
                recipient.save(update_fields=["status", "clicked_at", "opened_at"])
        except CampaignRecipient.DoesNotExist:
            pass

    return redirect(link.original_url)
