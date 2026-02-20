"""
eDocument notification functions.

Handles sending email/SMS notifications for the document signing workflow:
- When document is sent for signing (to all signers)
- When a signer completes their signature (to admin + next signer)
- When document is fully completed (to all parties)
"""

import logging

from django.conf import settings
from django.urls import reverse

from apps.core.services.email import send_email
from apps.core.services.sms import sms_service

logger = logging.getLogger(__name__)


def _get_absolute_url(path):
    """Build absolute URL from path."""
    site_url = getattr(settings, "SITE_URL", "http://localhost:8000")
    return f"{site_url.rstrip('/')}{path}"


def _get_signing_url(signer):
    """Get the signing URL for a signer.

    For users with accounts: tenant portal URL
    For external signers: public signing URL (future)
    """
    if signer.user:
        # Portal URL - tenant must log in
        path = reverse(
            "documents_tenant:edoc_detail",
            kwargs={"pk": signer.document.pk}
        )
        return _get_absolute_url(path)
    else:
        # External signer - no account
        # TODO: Implement token-based public signing URL
        # For now, return None and skip notification
        return None


def _build_signing_request_html(edoc, signer, signing_url):
    """Build HTML email for signing request."""
    property_name = ""
    if edoc.edoc_property:
        property_name = edoc.edoc_property.name
    elif edoc.lease and edoc.lease.unit:
        property_name = edoc.lease.unit.property.name if edoc.lease.unit.property else ""

    return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; }}
        .button {{ display: inline-block; background: #667eea; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; margin: 20px 0; }}
        .button:hover {{ background: #5a67d8; }}
        .footer {{ background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 8px 8px; }}
        .doc-info {{ background: #f8f9fa; padding: 15px; border-radius: 6px; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">Document Requires Your Signature</h1>
        </div>
        <div class="content">
            <p>Hello {signer.name},</p>
            <p>A document has been sent to you for signature. Please review and sign at your earliest convenience.</p>

            <div class="doc-info">
                <strong>Document:</strong> {edoc.title}<br>
                {"<strong>Property:</strong> " + property_name + "<br>" if property_name else ""}
                <strong>Your Role:</strong> {signer.get_role_display()}
            </div>

            <p style="text-align: center;">
                <a href="{signing_url}" class="button">Review & Sign Document</a>
            </p>

            <p style="font-size: 14px; color: #666;">
                If the button doesn't work, copy and paste this link into your browser:<br>
                <a href="{signing_url}">{signing_url}</a>
            </p>
        </div>
        <div class="footer">
            <p>This is an automated message from PropManager.</p>
        </div>
    </div>
</body>
</html>
"""


def _build_signature_received_html(edoc, signer_who_signed):
    """Build HTML email for signature received notification."""
    progress = edoc.signature_progress
    signers_status = []
    for s in edoc.signers.all():
        status = "Signed" if s.is_signed else "Pending"
        signers_status.append(f"{s.name} ({s.get_role_display()}): {status}")

    admin_url = _get_absolute_url(
        reverse("documents_admin:edoc_detail", kwargs={"pk": edoc.pk})
    )

    return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; }}
        .progress {{ background: #f0f0f0; border-radius: 10px; height: 20px; margin: 15px 0; overflow: hidden; }}
        .progress-bar {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); height: 100%; border-radius: 10px; }}
        .status-list {{ background: #f8f9fa; padding: 15px; border-radius: 6px; margin: 15px 0; }}
        .button {{ display: inline-block; background: #11998e; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; }}
        .footer {{ background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 8px 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">Signature Received</h1>
        </div>
        <div class="content">
            <p><strong>{signer_who_signed.name}</strong> ({signer_who_signed.get_role_display()}) has signed the document.</p>

            <p><strong>Document:</strong> {edoc.title}</p>

            <p><strong>Progress:</strong> {progress['signed']} of {progress['total']} signatures ({progress['percent']}%)</p>
            <div class="progress">
                <div class="progress-bar" style="width: {progress['percent']}%;"></div>
            </div>

            <div class="status-list">
                <strong>Signing Status:</strong><br>
                {"<br>".join(signers_status)}
            </div>

            <p>
                <a href="{admin_url}" class="button">View Document</a>
            </p>
        </div>
        <div class="footer">
            <p>This is an automated message from PropManager.</p>
        </div>
    </div>
</body>
</html>
"""


def _build_completed_html(edoc):
    """Build HTML email for document completion notification."""
    signers_info = []
    for s in edoc.signers.all():
        signed_date = s.signed_at.strftime("%B %d, %Y at %I:%M %p") if s.signed_at else "N/A"
        signers_info.append(f"{s.name} ({s.get_role_display()}): Signed on {signed_date}")

    admin_url = _get_absolute_url(
        reverse("documents_admin:edoc_detail", kwargs={"pk": edoc.pk})
    )

    return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; }}
        .success-box {{ background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 6px; margin: 15px 0; }}
        .signers-list {{ background: #f8f9fa; padding: 15px; border-radius: 6px; margin: 15px 0; }}
        .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; margin-right: 10px; }}
        .footer {{ background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 8px 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">Document Completed</h1>
        </div>
        <div class="content">
            <div class="success-box">
                <strong>All signatures have been collected!</strong><br>
                The document has been finalized and a PDF has been generated.
            </div>

            <p><strong>Document:</strong> {edoc.title}</p>
            <p><strong>Completed:</strong> {edoc.completed_at.strftime("%B %d, %Y at %I:%M %p") if edoc.completed_at else "N/A"}</p>

            <div class="signers-list">
                <strong>Signatures:</strong><br>
                {"<br>".join(signers_info)}
            </div>

            <p>
                <a href="{admin_url}" class="button">View Document</a>
            </p>
        </div>
        <div class="footer">
            <p>This is an automated message from PropManager.</p>
        </div>
    </div>
</body>
</html>
"""


def send_signing_request(edoc, signer):
    """
    Send notification to a signer that a document needs their signature.

    Args:
        edoc: EDocument instance
        signer: EDocumentSigner instance
    """
    if not signer.email:
        logger.warning(
            "Cannot send signing request - signer %s has no email",
            signer.pk
        )
        return False

    signing_url = _get_signing_url(signer)
    if not signing_url:
        # External signer without public URL support yet
        logger.info(
            "Skipping notification for external signer %s - public signing not implemented",
            signer.pk
        )
        return False

    subject = f"Document Requires Your Signature: {edoc.title}"
    text_body = (
        f"Hello {signer.name},\n\n"
        f"A document '{edoc.title}' has been sent to you for signature.\n\n"
        f"Please sign at: {signing_url}\n\n"
        f"Thank you."
    )
    html_body = _build_signing_request_html(edoc, signer, signing_url)

    try:
        send_email(
            subject=subject,
            message=text_body,
            recipient_list=[signer.email],
            html_message=html_body,
            source="edoc_signing_request",
        )
        logger.info(
            "Sent signing request to %s for edoc %s",
            signer.email, edoc.pk
        )

        # Also send SMS if signer has a user account with phone preference
        if signer.user:
            _send_sms_if_preferred(
                signer.user,
                f"PropManager: A document '{edoc.title}' needs your signature. Check your email for the signing link."
            )

        return True
    except Exception:
        logger.exception("Failed to send signing request to %s", signer.email)
        return False


def send_signature_received(edoc, signer_who_signed, admin_email=None):
    """
    Notify admin and next pending signer that a signature was received.

    Args:
        edoc: EDocument instance
        signer_who_signed: EDocumentSigner who just signed
        admin_email: Optional admin email to notify (defaults to created_by)
    """
    # Find admin email
    if not admin_email and edoc.created_by and edoc.created_by.email:
        admin_email = edoc.created_by.email

    subject = f"Signature Received: {edoc.title}"
    text_body = (
        f"{signer_who_signed.name} ({signer_who_signed.get_role_display()}) "
        f"has signed the document '{edoc.title}'.\n\n"
        f"Progress: {edoc.signature_progress['signed']}/{edoc.signature_progress['total']} signatures"
    )
    html_body = _build_signature_received_html(edoc, signer_who_signed)

    # Notify admin
    if admin_email:
        try:
            send_email(
                subject=subject,
                message=text_body,
                recipient_list=[admin_email],
                html_message=html_body,
                source="edoc_signature_received",
            )
            logger.info("Notified admin %s of signature on edoc %s", admin_email, edoc.pk)
        except Exception:
            logger.exception("Failed to notify admin of signature")

    # Find and notify next pending signer (if any)
    next_signer = edoc.signers.filter(signed_at__isnull=True).first()
    if next_signer and next_signer.email:
        signing_url = _get_signing_url(next_signer)
        if signing_url:
            next_subject = f"Your Turn to Sign: {edoc.title}"
            next_text = (
                f"Hello {next_signer.name},\n\n"
                f"It's now your turn to sign '{edoc.title}'. "
                f"Previous signers have completed their signatures.\n\n"
                f"Please sign at: {signing_url}"
            )
            try:
                send_email(
                    subject=next_subject,
                    message=next_text,
                    recipient_list=[next_signer.email],
                    html_message=_build_signing_request_html(edoc, next_signer, signing_url),
                    source="edoc_next_signer",
                )
                logger.info("Notified next signer %s", next_signer.email)
            except Exception:
                logger.exception("Failed to notify next signer")


def send_document_completed(edoc):
    """
    Notify all parties that the document is fully executed.

    Args:
        edoc: EDocument instance (should have status=completed)
    """
    subject = f"Document Completed: {edoc.title}"
    text_body = (
        f"The document '{edoc.title}' has been fully signed by all parties.\n\n"
        f"A PDF copy has been generated and is available for download."
    )
    html_body = _build_completed_html(edoc)

    # Collect all unique emails to notify
    recipients = set()

    # Add admin/creator
    if edoc.created_by and edoc.created_by.email:
        recipients.add(edoc.created_by.email)

    # Add all signers
    for signer in edoc.signers.all():
        if signer.email:
            recipients.add(signer.email)

    # Send to all recipients
    for email in recipients:
        try:
            send_email(
                subject=subject,
                message=text_body,
                recipient_list=[email],
                html_message=html_body,
                source="edoc_completed",
            )
            logger.info("Sent completion notification to %s for edoc %s", email, edoc.pk)
        except Exception:
            logger.exception("Failed to send completion notification to %s", email)

    # Send SMS to signers with phone preference
    for signer in edoc.signers.all():
        if signer.user:
            _send_sms_if_preferred(
                signer.user,
                f"PropManager: Document '{edoc.title}' is now fully signed. Check your email for the PDF."
            )


def _send_sms_if_preferred(user, message):
    """Send SMS to user if they prefer SMS notifications and have a phone number."""
    try:
        # Check user's notification preference
        preferred = getattr(user, "preferred_contact", "email")
        phone = getattr(user, "phone_number", None)

        if preferred in ("sms", "both") and phone:
            sms_service.send_sms(to=phone, body=message)
            logger.info("Sent SMS to %s", phone)
    except Exception:
        logger.exception("Failed to send SMS to user %s", user.pk)
