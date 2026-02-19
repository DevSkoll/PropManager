"""
Django-Q2 tasks for marketing campaign email sending and scheduling.
"""

import logging
import re
import secrets

from django.conf import settings
from django.utils import timezone

from apps.accounts.models import User
from apps.core.services.email import send_email
from apps.leases.models import Lease

from .models import Campaign, CampaignLink, CampaignRecipient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Segment Resolution
# ---------------------------------------------------------------------------


def _resolve_segment_tenants(segment):
    """Resolve a single CampaignSegment to a queryset of User IDs."""
    filter_type = segment.filter_type
    filter_value = segment.filter_value or {}

    if filter_type == "all":
        return User.objects.filter(role="tenant", is_active=True).values_list(
            "id", flat=True
        )

    if filter_type == "by_property":
        property_id = filter_value.get("property_id")
        if property_id:
            return Lease.objects.filter(
                unit__property_id=property_id, status="active"
            ).values_list("tenant_id", flat=True)
        return User.objects.none().values_list("id", flat=True)

    if filter_type == "by_lease_status":
        status = filter_value.get("status")
        if status:
            return Lease.objects.filter(status=status).values_list(
                "tenant_id", flat=True
            )
        return User.objects.none().values_list("id", flat=True)

    if filter_type == "by_move_in_date":
        start = filter_value.get("start")
        end = filter_value.get("end")
        qs = User.objects.filter(role="tenant", is_active=True)
        if start:
            qs = qs.filter(tenant_profile__move_in_date__gte=start)
        if end:
            qs = qs.filter(tenant_profile__move_in_date__lte=end)
        return qs.values_list("id", flat=True)

    return User.objects.none().values_list("id", flat=True)


# ---------------------------------------------------------------------------
# Task: Generate Campaign Recipients
# ---------------------------------------------------------------------------


def generate_campaign_recipients(campaign_id):
    """Resolve all campaign segments and create CampaignRecipient records."""
    try:
        campaign = Campaign.objects.get(pk=campaign_id)
    except Campaign.DoesNotExist:
        logger.error("Campaign %s does not exist.", campaign_id)
        return 0

    tenant_ids = set()
    for segment in campaign.segments.all():
        tenant_ids.update(_resolve_segment_tenants(segment))

    tenants = User.objects.filter(id__in=tenant_ids, is_active=True)

    created_count = 0
    for tenant in tenants:
        _, created = CampaignRecipient.objects.get_or_create(
            campaign=campaign,
            tenant=tenant,
            defaults={"email": tenant.email},
        )
        if created:
            created_count += 1

    logger.info(
        "Generated %d recipients for campaign %s (%s).",
        created_count,
        campaign.pk,
        campaign.name,
    )
    return created_count


# ---------------------------------------------------------------------------
# Task: Process Campaign Links for Tracking
# ---------------------------------------------------------------------------


def _process_links_for_tracking(campaign):
    """
    Find all URLs in body_html, create CampaignLink records,
    and return the body_html with URLs replaced by tracking URLs.
    """
    body_html = campaign.body_html
    if not body_html:
        return body_html

    # Match href="..." URLs in anchor tags
    url_pattern = re.compile(r'href=["\']((https?://[^"\']+))["\']')
    urls_found = set(url_pattern.findall(body_html))

    base_url = getattr(settings, "SITE_URL", "http://localhost:8000")

    link_map = {}  # original_url -> tracking_token
    for full_match, url in urls_found:
        # Skip tracking URLs (avoid double-tracking)
        if "/marketing/track/" in url:
            continue

        link, created = CampaignLink.objects.get_or_create(
            campaign=campaign,
            original_url=url,
            defaults={"tracking_token": secrets.token_urlsafe(32)},
        )
        link_map[url] = link.tracking_token

    return body_html, link_map


def _replace_links_in_html(body_html, link_map, recipient_pk, base_url):
    """Replace original URLs in HTML with tracking redirect URLs."""
    result = body_html
    for original_url, token in link_map.items():
        tracking_url = f"{base_url}/marketing/track/click/{token}/?rid={recipient_pk}"
        result = result.replace(
            f'href="{original_url}"',
            f'href="{tracking_url}"',
        )
        result = result.replace(
            f"href='{original_url}'",
            f"href='{tracking_url}'",
        )
    return result


# ---------------------------------------------------------------------------
# Task: Send Individual Campaign Email
# ---------------------------------------------------------------------------


def send_campaign_email(recipient_id):
    """Send a single campaign email to a specific recipient."""
    try:
        recipient = CampaignRecipient.objects.select_related(
            "campaign", "tenant"
        ).get(pk=recipient_id)
    except CampaignRecipient.DoesNotExist:
        logger.error("CampaignRecipient %s does not exist.", recipient_id)
        return False

    campaign = recipient.campaign
    base_url = getattr(settings, "SITE_URL", "http://localhost:8000")

    # Build the HTML body with tracking pixel and link tracking
    body_html = campaign.body_html or ""

    # Process links for tracking
    link_map = {}
    for link in campaign.links.all():
        link_map[link.original_url] = link.tracking_token

    if link_map:
        body_html = _replace_links_in_html(
            body_html, link_map, str(recipient.pk), base_url
        )

    # Append tracking pixel
    pixel_url = f"{base_url}/marketing/track/open/{recipient.pk}/"
    tracking_pixel_tag = (
        f'<img src="{pixel_url}" width="1" height="1" alt="" '
        f'style="display:none;border:0;" />'
    )
    body_html += tracking_pixel_tag

    body_text = campaign.body_text or ""

    try:
        success = send_email(
            subject=campaign.subject,
            message=body_text,
            recipient_list=[recipient.email],
            html_message=body_html,
        )
        if success:
            recipient.status = "sent"
            recipient.sent_at = timezone.now()
            recipient.save(update_fields=["status", "sent_at"])
            return True
        else:
            recipient.status = "failed"
            recipient.save(update_fields=["status"])
            return False
    except Exception:
        logger.exception(
            "Failed to send campaign email to %s for campaign %s.",
            recipient.email,
            campaign.pk,
        )
        recipient.status = "failed"
        recipient.save(update_fields=["status"])
        return False


# ---------------------------------------------------------------------------
# Task: Send Campaign (orchestrator)
# ---------------------------------------------------------------------------


def send_campaign(campaign_id):
    """
    Main campaign send task.
    1. Generate recipients from segments.
    2. Process links in HTML for tracking.
    3. Send each email.
    4. Update campaign status.
    """
    try:
        campaign = Campaign.objects.get(pk=campaign_id)
    except Campaign.DoesNotExist:
        logger.error("Campaign %s does not exist.", campaign_id)
        return

    if campaign.status not in ("sending", "scheduled"):
        logger.warning(
            "Campaign %s has status '%s'; expected 'sending' or 'scheduled'. Aborting.",
            campaign_id,
            campaign.status,
        )
        return

    # Mark as sending
    campaign.status = "sending"
    campaign.save(update_fields=["status"])

    # Step 1: Generate recipients
    generate_campaign_recipients(campaign_id)

    # Step 2: Process links for tracking
    if campaign.body_html:
        result = _process_links_for_tracking(campaign)
        if result:
            # Links have been created in the database; individual emails
            # will use them when building per-recipient HTML.
            pass

    # Step 3: Send emails to each recipient
    recipients = campaign.recipients.filter(status="pending")
    sent_count = 0
    failed_count = 0

    for recipient in recipients:
        success = send_campaign_email(str(recipient.pk))
        if success:
            sent_count += 1
        else:
            failed_count += 1

    # Step 4: Update campaign status
    campaign.status = "sent"
    campaign.sent_at = timezone.now()
    campaign.save(update_fields=["status", "sent_at"])

    logger.info(
        "Campaign %s (%s) completed: %d sent, %d failed.",
        campaign.pk,
        campaign.name,
        sent_count,
        failed_count,
    )


# ---------------------------------------------------------------------------
# Task: Process Scheduled Campaigns
# ---------------------------------------------------------------------------


def process_scheduled_campaigns():
    """
    Periodic task: find campaigns with status=scheduled and
    scheduled_at <= now, then start sending them.
    """
    now = timezone.now()
    scheduled_campaigns = Campaign.objects.filter(
        status="scheduled",
        scheduled_at__lte=now,
    )

    count = 0
    for campaign in scheduled_campaigns:
        campaign.status = "sending"
        campaign.save(update_fields=["status"])

        try:
            from django_q.tasks import async_task

            async_task("apps.marketing.tasks.send_campaign", str(campaign.pk))
        except ImportError:
            send_campaign(str(campaign.pk))

        count += 1
        logger.info(
            "Scheduled campaign %s (%s) triggered for sending.",
            campaign.pk,
            campaign.name,
        )

    return count
