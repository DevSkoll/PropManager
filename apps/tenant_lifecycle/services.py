"""
Onboarding Service.

Handles all business logic for the tenant onboarding process including:
- Session creation and management
- Invitation sending (email/SMS)
- Document generation from templates
- Payment processing
- Completion notifications
"""

import logging
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.core.services.email import send_email
from apps.core.services.sms import sms_service
from apps.core.url_utils import get_absolute_url

from .models import (
    OnboardingDocument,
    OnboardingPayment,
    OnboardingSession,
    OnboardingStepLog,
    OnboardingTemplate,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class OnboardingService:
    """Service for managing tenant onboarding."""

    # =========================================================================
    # Session Creation
    # =========================================================================

    @staticmethod
    def create_session(
        unit,
        prospective_email,
        prospective_first_name,
        prospective_last_name,
        prospective_phone="",
        template=None,
        lease=None,
        created_by=None,
        notes="",
        send_invitation=True,
    ):
        """
        Create a new onboarding session for a prospective tenant.

        Args:
            unit: Unit the tenant will be moving into
            prospective_email: Email address of the prospective tenant
            prospective_first_name: First name
            prospective_last_name: Last name
            prospective_phone: Phone number (optional)
            template: OnboardingTemplate to use (defaults to property's default)
            lease: Existing Lease to link (optional)
            created_by: User who created the session
            notes: Internal notes
            send_invitation: Whether to send invitation immediately

        Returns:
            OnboardingSession instance
        """
        # Get template
        if not template:
            template = OnboardingTemplate.objects.filter(
                property=unit.property,
                is_active=True,
                is_default=True,
            ).first()

            if not template:
                # Get any active template for the property
                template = OnboardingTemplate.objects.filter(
                    property=unit.property,
                    is_active=True,
                ).first()

        if not template:
            raise ValueError(f"No active onboarding template found for property {unit.property}")

        # Initialize steps_completed based on template config
        steps_completed = {}

        with transaction.atomic():
            session = OnboardingSession.objects.create(
                template=template,
                unit=unit,
                lease=lease,
                prospective_email=prospective_email,
                prospective_phone=prospective_phone,
                prospective_first_name=prospective_first_name,
                prospective_last_name=prospective_last_name,
                steps_completed=steps_completed,
                notes=notes,
                created_by=created_by,
            )

            logger.info(
                "Created onboarding session %s for %s at unit %s",
                session.pk, prospective_email, unit
            )

            # Send invitation if requested
            if send_invitation:
                OnboardingService.send_invitation(session)

        return session

    # =========================================================================
    # Invitations
    # =========================================================================

    @staticmethod
    def send_invitation(session, method="both"):
        """
        Send onboarding invitation to prospective tenant.

        Args:
            session: OnboardingSession instance
            method: 'email', 'sms', or 'both'

        Returns:
            dict with 'email_sent' and 'sms_sent' booleans
        """
        result = {"email_sent": False, "sms_sent": False}
        template = session.template

        # Build onboarding URL
        onboarding_path = reverse(
            "tenant_lifecycle:onboarding_start",
            kwargs={"token": session.access_token}
        )
        onboarding_url = get_absolute_url(onboarding_path)

        # Send email
        if method in ("email", "both"):
            result["email_sent"] = OnboardingService._send_invitation_email(
                session, template, onboarding_url
            )

        # Send SMS
        if method in ("sms", "both") and session.prospective_phone:
            result["sms_sent"] = OnboardingService._send_invitation_sms(
                session, template, onboarding_url
            )

        # Update invitation timestamp
        session.invitation_sent_at = timezone.now()
        session.save(update_fields=["invitation_sent_at", "updated_at"])

        return result

    @staticmethod
    def _send_invitation_email(session, template, onboarding_url):
        """Send invitation email."""
        # Build email body
        if template.invitation_email_body:
            body = template.invitation_email_body.replace("{{link}}", onboarding_url)
        else:
            body = f"""
Hello {session.prospective_first_name},

Welcome! You've been invited to complete your move-in process for {session.unit}.

Please click the link below to get started:
{onboarding_url}

This link will expire in {template.link_expiry_days} days.

If you have any questions, please contact your property manager.

Thank you!
"""

        # Build HTML email
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; }}
        .button {{ display: inline-block; background: #667eea; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; margin: 20px 0; }}
        .footer {{ background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 8px 8px; }}
        .unit-info {{ background: #f8f9fa; padding: 15px; border-radius: 6px; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">Welcome to Your New Home!</h1>
        </div>
        <div class="content">
            <p>Hello {session.prospective_first_name},</p>
            <p>You've been invited to complete your move-in process. This simple online process will help us get everything ready for your arrival.</p>

            <div class="unit-info">
                <strong>Unit:</strong> {session.unit}<br>
                <strong>Property:</strong> {session.unit.property.name if session.unit.property else 'N/A'}
            </div>

            <p style="text-align: center;">
                <a href="{onboarding_url}" class="button">Start Move-In Process</a>
            </p>

            <p style="font-size: 14px; color: #666;">
                This link will expire in {template.link_expiry_days} days.<br>
                If the button doesn't work, copy and paste this link into your browser:<br>
                <a href="{onboarding_url}">{onboarding_url}</a>
            </p>
        </div>
        <div class="footer">
            <p>This is an automated message from PropManager.</p>
        </div>
    </div>
</body>
</html>
"""

        try:
            send_email(
                subject=template.invitation_email_subject or "Welcome! Complete Your Move-In Process",
                message=body,
                recipient_list=[session.prospective_email],
                html_message=html_body,
                source="onboarding_invitation",
            )
            logger.info("Sent onboarding invitation email to %s", session.prospective_email)
            return True
        except Exception:
            logger.exception("Failed to send onboarding invitation email to %s", session.prospective_email)
            return False

    @staticmethod
    def _send_invitation_sms(session, template, onboarding_url):
        """Send invitation SMS."""
        if template.invitation_sms_body:
            message = template.invitation_sms_body.replace("{{link}}", onboarding_url)
        else:
            message = (
                f"Welcome {session.prospective_first_name}! "
                f"Complete your move-in process: {onboarding_url}"
            )

        try:
            sms_service.send_sms(
                to=session.prospective_phone,
                body=message,
            )
            logger.info("Sent onboarding invitation SMS to %s", session.prospective_phone)
            return True
        except Exception:
            logger.exception("Failed to send onboarding invitation SMS to %s", session.prospective_phone)
            return False

    # =========================================================================
    # Account Creation
    # =========================================================================

    @staticmethod
    def create_tenant_account(session, first_name, last_name, phone_number="", preferred_contact="email"):
        """
        Create a user account for the onboarding tenant.

        Args:
            session: OnboardingSession instance
            first_name: First name
            last_name: Last name
            phone_number: Phone number
            preferred_contact: Contact preference ('email', 'sms', 'both')

        Returns:
            User instance
        """
        with transaction.atomic():
            # Check if user already exists by email
            existing_user = User.objects.filter(email=session.prospective_email).first()
            if existing_user:
                session.tenant = existing_user
                session.save(update_fields=["tenant", "updated_at"])
                return existing_user

            # Generate unique username from email
            base_username = session.prospective_email.split("@")[0]
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            # Create new user
            user = User.objects.create(
                username=username,
                email=session.prospective_email,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                preferred_contact=preferred_contact,
                role="tenant",
                is_active=True,
            )

            # Link to session
            session.tenant = user
            session.save(update_fields=["tenant", "updated_at"])

            logger.info("Created tenant account %s for onboarding session %s", user.email, session.pk)

            return user

    # =========================================================================
    # Document Management
    # =========================================================================

    @staticmethod
    def create_session_documents(session):
        """
        Create EDocument instances from template documents.

        Should be called when tenant reaches the documents step.

        Args:
            session: OnboardingSession instance

        Returns:
            list of OnboardingDocument instances
        """
        from apps.documents.models import EDocument, EDocumentSigner

        if not session.template:
            return []

        template_docs = session.template.documents.select_related("edocument_template").all()
        created_docs = []

        with transaction.atomic():
            for template_doc in template_docs:
                # Check if already created
                existing = OnboardingDocument.objects.filter(
                    session=session,
                    template_document=template_doc,
                ).first()
                if existing:
                    created_docs.append(existing)
                    continue

                # Create EDocument from template
                edoc_template = template_doc.edocument_template
                edoc = EDocument.objects.create(
                    template=edoc_template,
                    title=edoc_template.name,
                    content=edoc_template.content,
                    lease=session.lease,
                    tenant=session.tenant,
                    edoc_property=session.unit.property if session.unit else None,
                    status="pending",
                    created_by=session.created_by,
                )

                # Add tenant as signer
                if session.tenant:
                    EDocumentSigner.objects.create(
                        document=edoc,
                        user=session.tenant,
                        name=f"{session.tenant.first_name} {session.tenant.last_name}",
                        email=session.tenant.email,
                        role="tenant",
                        order=1,
                    )

                # Create tracking record
                onboarding_doc = OnboardingDocument.objects.create(
                    session=session,
                    template_document=template_doc,
                    edocument=edoc,
                    is_required=template_doc.is_required,
                )
                created_docs.append(onboarding_doc)

                logger.info(
                    "Created EDocument %s for onboarding session %s",
                    edoc.pk, session.pk
                )

        return created_docs

    @staticmethod
    def check_documents_complete(session):
        """
        Check if all required documents have been signed.

        Returns:
            bool
        """
        required_docs = OnboardingDocument.objects.filter(
            session=session,
            is_required=True,
        )

        for doc in required_docs:
            if not doc.is_signed:
                return False

        return True

    # =========================================================================
    # Payment Management
    # =========================================================================

    @staticmethod
    def create_session_payments(session):
        """
        Create OnboardingPayment records from template fees.

        Should be called when tenant reaches the payments step.

        Args:
            session: OnboardingSession instance

        Returns:
            list of OnboardingPayment instances
        """
        if not session.template:
            return []

        template_fees = session.template.fees.all()
        created_payments = []

        with transaction.atomic():
            for fee in template_fees:
                # Check if already created
                existing = OnboardingPayment.objects.filter(
                    session=session,
                    template_fee=fee,
                ).first()
                if existing:
                    created_payments.append(existing)
                    continue

                # Calculate amount
                amount = fee.get_amount_for_lease(session.lease)

                payment = OnboardingPayment.objects.create(
                    session=session,
                    template_fee=fee,
                    fee_type=fee.fee_type,
                    description=fee.name,
                    amount=amount,
                    is_refundable=fee.is_refundable,
                )
                created_payments.append(payment)

                logger.info(
                    "Created OnboardingPayment %s ($%s) for session %s",
                    fee.name, amount, session.pk
                )

        return created_payments

    @staticmethod
    def process_payment(session, payment_ids, gateway_provider, payment_method_token=None):
        """
        Process payments for onboarding session.

        Args:
            session: OnboardingSession instance
            payment_ids: list of OnboardingPayment IDs to process
            gateway_provider: Payment gateway to use
            payment_method_token: Token from client-side payment form

        Returns:
            dict with 'success', 'invoice', 'payment', 'error'
        """
        from apps.billing.models import Invoice, InvoiceLineItem
        from apps.billing.services import PaymentService

        payments = OnboardingPayment.objects.filter(
            pk__in=payment_ids,
            session=session,
            status="pending",
        )

        if not payments.exists():
            return {"success": False, "error": "No pending payments found"}

        total_amount = sum(p.amount for p in payments)

        try:
            with transaction.atomic():
                # Create invoice
                invoice = Invoice.objects.create(
                    tenant=session.tenant,
                    lease=session.lease,
                    status="pending",
                    due_date=timezone.now().date(),
                    subtotal=total_amount,
                    total=total_amount,
                    notes="Onboarding fees",
                )

                # Add line items
                for payment in payments:
                    InvoiceLineItem.objects.create(
                        invoice=invoice,
                        description=payment.description,
                        amount=payment.amount,
                        quantity=1,
                    )
                    payment.invoice = invoice
                    payment.status = "processing"
                    payment.save(update_fields=["invoice", "status", "updated_at"])

                # Process payment
                payment_service = PaymentService(gateway_provider)
                result = payment_service.process_payment(
                    invoice=invoice,
                    amount=total_amount,
                    payment_method_token=payment_method_token,
                    tenant=session.tenant,
                )

                if result.get("success"):
                    # Update payment records
                    for ob_payment in payments:
                        ob_payment.status = "completed"
                        ob_payment.payment = result.get("payment")
                        ob_payment.save(update_fields=["status", "payment", "updated_at"])

                    logger.info(
                        "Processed onboarding payments for session %s, total: $%s",
                        session.pk, total_amount
                    )

                    return {
                        "success": True,
                        "invoice": invoice,
                        "payment": result.get("payment"),
                    }
                else:
                    # Payment failed
                    for ob_payment in payments:
                        ob_payment.status = "failed"
                        ob_payment.last_error = result.get("error", "Payment failed")
                        ob_payment.attempt_count += 1
                        ob_payment.save(update_fields=["status", "last_error", "attempt_count", "updated_at"])

                    return {
                        "success": False,
                        "error": result.get("error", "Payment failed"),
                    }

        except Exception as e:
            logger.exception("Error processing onboarding payments for session %s", session.pk)
            return {"success": False, "error": str(e)}

    @staticmethod
    def check_payments_complete(session):
        """
        Check if all required payments have been completed.

        Returns:
            bool
        """
        pending_required = OnboardingPayment.objects.filter(
            session=session,
            template_fee__is_required=True,
            status__in=["pending", "processing", "failed"],
        ).exists()

        return not pending_required

    # =========================================================================
    # Session Completion
    # =========================================================================

    @staticmethod
    def complete_session(session):
        """
        Mark onboarding session as completed and finalize all data.

        - Links tenant to lease
        - Transfers personal info to TenantProfile
        - Updates lease move-in date from schedule
        - Generates move-in invoices
        - Sends completion notifications

        Args:
            session: OnboardingSession instance
        """
        from datetime import datetime
        from apps.accounts.models import TenantProfile

        session.status = "completed"
        session.completed_at = timezone.now()
        session.save(update_fields=["status", "completed_at"])

        # Link tenant to lease if not already, and clear prospective fields
        if session.lease and session.tenant:
            lease = session.lease
            update_fields = []

            if not lease.tenant:
                lease.tenant = session.tenant
                # Clear prospective fields now that tenant is linked
                lease.prospective_first_name = ""
                lease.prospective_last_name = ""
                lease.prospective_email = ""
                lease.prospective_phone = ""
                update_fields.extend([
                    "tenant",
                    "prospective_first_name",
                    "prospective_last_name",
                    "prospective_email",
                    "prospective_phone",
                ])

            # Update move-in date from schedule if collected
            move_in_data = session.steps_completed.get("move_in_schedule_data", {})
            if move_in_data.get("date"):
                try:
                    move_in_date = datetime.fromisoformat(move_in_data["date"]).date()
                    lease.move_in_date = move_in_date
                    update_fields.append("move_in_date")
                except (ValueError, TypeError):
                    logger.warning("Invalid move-in date format in session %s", session.pk)

            if update_fields:
                lease.save(update_fields=update_fields)

        # Transfer personal info to TenantProfile
        if session.tenant and session.collected_data.get("personal_info"):
            OnboardingService._update_tenant_profile(session)

        # Generate move-in invoices from template fees
        OnboardingService.generate_move_in_invoices(session)

        # Send completion notifications
        OnboardingService.send_completion_notification(session)

        logger.info("Completed onboarding session %s", session.pk)

    @staticmethod
    def _update_tenant_profile(session):
        """
        Transfer collected personal info to tenant's profile.

        Args:
            session: OnboardingSession instance
        """
        from datetime import datetime
        from apps.accounts.models import TenantProfile

        personal_info = session.collected_data.get("personal_info", {})
        if not personal_info:
            return

        # Get or create tenant profile
        profile, created = TenantProfile.objects.get_or_create(user=session.tenant)

        # Update fields from collected data
        update_fields = []

        if personal_info.get("date_of_birth"):
            try:
                profile.date_of_birth = datetime.fromisoformat(personal_info["date_of_birth"]).date()
                update_fields.append("date_of_birth")
            except (ValueError, TypeError):
                logger.warning("Invalid DOB format in session %s", session.pk)

        if personal_info.get("ssn_last_four"):
            profile.ssn_last_four = personal_info["ssn_last_four"]
            update_fields.append("ssn_last_four")

        if personal_info.get("drivers_license_state"):
            profile.drivers_license_state = personal_info["drivers_license_state"]
            update_fields.append("drivers_license_state")

        if personal_info.get("drivers_license_number"):
            profile.drivers_license_number = personal_info["drivers_license_number"]
            update_fields.append("drivers_license_number")

        if update_fields:
            profile.save(update_fields=update_fields)
            logger.info("Updated TenantProfile for user %s with %d fields", session.tenant.pk, len(update_fields))

    @staticmethod
    def generate_move_in_invoices(session):
        """
        Generate invoices for move-in fees defined in the template.

        Creates an Invoice with line items for each required fee.
        The tenant can then pay these through the normal billing portal.

        Args:
            session: OnboardingSession instance
        """
        if not session.template or not session.lease or not session.tenant:
            logger.warning(
                "Cannot generate invoices for session %s: missing template, lease, or tenant",
                session.pk
            )
            return

        from apps.billing.models import Invoice, InvoiceLineItem
        from apps.billing.services import InvoiceService

        # Get required template fees
        template_fees = session.template.fees.filter(is_required=True)
        if not template_fees.exists():
            logger.info("No required fees for session %s", session.pk)
            return

        # Calculate total and prepare line items
        line_items = []
        total = Decimal("0.00")

        for fee in template_fees:
            amount = fee.get_amount_for_lease(session.lease)
            line_items.append({
                "fee": fee,
                "amount": amount,
            })
            total += amount

        if total <= 0:
            logger.info("No positive fees to invoice for session %s", session.pk)
            return

        # Generate invoice number
        invoice_number = InvoiceService.generate_invoice_number()

        # Determine due date (lease start date or today)
        due_date = session.lease.start_date or timezone.now().date()

        # Create the invoice
        invoice = Invoice.objects.create(
            invoice_number=invoice_number,
            tenant=session.tenant,
            lease=session.lease,
            status="issued",
            issue_date=timezone.now().date(),
            due_date=due_date,
            total_amount=total,
            notes=f"Move-in fees for {session.unit} - generated from onboarding",
        )

        # Create line items
        for item in line_items:
            fee = item["fee"]
            amount = item["amount"]

            InvoiceLineItem.objects.create(
                invoice=invoice,
                charge_type=fee.fee_type,
                description=fee.name,
                unit_price=amount,
                quantity=1,
            )

            # Create OnboardingPayment record for tracking
            OnboardingPayment.objects.create(
                session=session,
                template_fee=fee,
                fee_type=fee.fee_type,
                description=fee.name,
                amount=amount,
                is_refundable=fee.is_refundable,
                status="pending",  # Will be updated when tenant pays
                invoice=invoice,
            )

        logger.info(
            "Generated move-in invoice %s for session %s (total: $%s)",
            invoice_number, session.pk, total
        )

    @staticmethod
    def send_completion_notification(session):
        """
        Send notifications that onboarding is complete.

        Notifies:
        - The tenant (welcome email)
        - The property manager/admin
        """
        # Tenant notification
        if session.tenant and session.tenant.email:
            try:
                welcome_html = OnboardingService._build_welcome_email(session)
                send_email(
                    subject=f"Welcome Home! - {session.unit}",
                    message=f"Congratulations! Your move-in process is complete for {session.unit}.",
                    recipient_list=[session.tenant.email],
                    html_message=welcome_html,
                    source="onboarding_complete_tenant",
                )
            except Exception:
                logger.exception("Failed to send completion email to tenant %s", session.tenant.email)

        # Admin notification
        if session.created_by and session.created_by.email:
            try:
                admin_url = get_absolute_url(
                    reverse("tenant_lifecycle_admin:admin_session_detail", kwargs={"pk": session.pk})
                )
                send_email(
                    subject=f"Onboarding Complete: {session.prospective_full_name}",
                    message=(
                        f"{session.prospective_full_name} has completed onboarding for {session.unit}.\n\n"
                        f"View details: {admin_url}"
                    ),
                    recipient_list=[session.created_by.email],
                    source="onboarding_complete_admin",
                )
            except Exception:
                logger.exception("Failed to send completion email to admin")

    @staticmethod
    def _build_welcome_email(session):
        """Build HTML welcome email for completed onboarding."""
        template = session.template
        welcome_message = template.welcome_message if template else ""
        property_rules = template.property_rules if template else ""

        return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center; }}
        .content {{ background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; }}
        .success-box {{ background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 6px; margin: 15px 0; }}
        .info-box {{ background: #f8f9fa; padding: 15px; border-radius: 6px; margin: 15px 0; }}
        .footer {{ background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 8px 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">Welcome Home!</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Your move-in process is complete</p>
        </div>
        <div class="content">
            <div class="success-box">
                <strong>Congratulations, {session.prospective_first_name}!</strong><br>
                You've completed all the move-in steps for {session.unit}.
            </div>

            {"<div class='info-box'><strong>A Message From Your Property Manager:</strong><br>" + welcome_message + "</div>" if welcome_message else ""}

            {"<div class='info-box'><strong>Property Rules & Guidelines:</strong><br>" + property_rules.replace(chr(10), '<br>') + "</div>" if property_rules else ""}

            <p>If you have any questions or need assistance, please don't hesitate to contact your property manager.</p>
        </div>
        <div class="footer">
            <p>This is an automated message from PropManager.</p>
        </div>
    </div>
</body>
</html>
"""

    # =========================================================================
    # Utility Methods
    # =========================================================================

    @staticmethod
    def get_session_summary(session):
        """
        Get a summary of the session's progress.

        Returns:
            dict with progress information
        """
        template = session.template
        enabled_steps = template.get_enabled_steps() if template else []

        steps_status = []
        for step in enabled_steps:
            step_name = step["name"]
            steps_status.append({
                "name": step_name,
                "label": step_name.replace("_", " ").title(),
                "required": step["required"],
                "completed": step_name in session.steps_completed,
                "completed_at": session.steps_completed.get(step_name),
            })

        # Get counts
        total_docs = OnboardingDocument.objects.filter(session=session).count()
        signed_docs = OnboardingDocument.objects.filter(session=session, signed_at__isnull=False).count()

        total_payments = OnboardingPayment.objects.filter(session=session).count()
        completed_payments = OnboardingPayment.objects.filter(session=session, status="completed").count()

        return {
            "progress_percent": session.get_progress_percent(),
            "steps": steps_status,
            "current_step": session.current_step,
            "documents": {"total": total_docs, "signed": signed_docs},
            "payments": {"total": total_payments, "completed": completed_payments},
        }

    @staticmethod
    def log_step_attempt(session, step_name, request, data=None):
        """
        Log an attempt at an onboarding step.

        Args:
            session: OnboardingSession instance
            step_name: Name of the step
            request: HTTP request
            data: Optional data snapshot
        """
        from .decorators import get_client_ip

        existing_attempts = OnboardingStepLog.objects.filter(
            session=session,
            step_name=step_name,
        ).count()

        OnboardingStepLog.objects.create(
            session=session,
            step_name=step_name,
            attempt_number=existing_attempts + 1,
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            data_snapshot=data or {},
        )
