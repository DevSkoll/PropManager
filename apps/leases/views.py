import secrets
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.core.decorators import admin_required, tenant_required

from .forms import LeaseForm, LeaseTermForm, SignLeaseForm
from .models import Lease, LeaseSignature, LeaseTerm


# =============================================================================
# Admin Views
# =============================================================================

@admin_required
def admin_lease_list(request):
    leases = Lease.objects.select_related("unit", "unit__property", "tenant").all()

    # Separate pending onboarding leases (no tenant assigned)
    pending_onboarding = leases.filter(tenant__isnull=True).order_by("-created_at")
    pending_count = pending_onboarding.count()

    status_filter = request.GET.get("status")
    if status_filter == "pending_onboarding":
        leases = pending_onboarding
    elif status_filter:
        leases = leases.filter(status=status_filter, tenant__isnull=False)
    else:
        # Default: show leases with tenants
        leases = leases.filter(tenant__isnull=False)

    return render(request, "leases/admin_lease_list.html", {
        "leases": leases,
        "pending_onboarding": pending_onboarding,
        "pending_count": pending_count,
        "status_filter": status_filter,
        "status_choices": Lease.STATUS_CHOICES,
    })


@admin_required
def admin_lease_create(request):
    form = LeaseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        lease = form.save(commit=False)
        lease.created_by = request.user
        lease.save()
        messages.success(request, "Lease created successfully.")
        return redirect("leases_admin:lease_detail", pk=lease.pk)
    return render(request, "leases/admin_lease_form.html", {"form": form, "title": "Create Lease"})


@admin_required
def admin_lease_detail(request, pk):
    lease = get_object_or_404(
        Lease.objects.select_related("unit", "unit__property", "tenant")
        .prefetch_related("terms", "occupants", "pets", "fees", "signatures", "documents", "edocuments"),
        pk=pk
    )
    # Get linked documents and eDocuments
    documents = lease.documents.filter(deleted_at__isnull=True).order_by("-created_at")
    edocuments = lease.edocuments.all().order_by("-created_at")

    return render(request, "leases/admin_lease_detail.html", {
        "lease": lease,
        "terms": lease.terms.all(),
        "occupants": lease.occupants.all(),
        "pets": lease.pets.all(),
        "fees": lease.fees.all(),
        "signatures": lease.signatures.all(),
        "documents": documents,
        "edocuments": edocuments,
    })


@admin_required
def admin_lease_edit(request, pk):
    lease = get_object_or_404(Lease, pk=pk)
    form = LeaseForm(request.POST or None, instance=lease)
    if request.method == "POST" and form.is_valid():
        lease = form.save(commit=False)
        lease.updated_by = request.user
        lease.save()
        messages.success(request, "Lease updated successfully.")
        return redirect("leases_admin:lease_detail", pk=lease.pk)
    return render(request, "leases/admin_lease_form.html", {"form": form, "title": "Edit Lease", "lease": lease})


@admin_required
def admin_lease_add_term(request, pk):
    lease = get_object_or_404(Lease, pk=pk)
    form = LeaseTermForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        term = form.save(commit=False)
        term.lease = lease
        term.save()
        messages.success(request, "Term added to lease.")
        return redirect("leases_admin:lease_detail", pk=lease.pk)
    return render(request, "leases/admin_lease_term_form.html", {"form": form, "lease": lease})


@admin_required
def admin_lease_start_onboarding(request, pk):
    """Create onboarding session for a pending lease (no tenant assigned)."""
    lease = get_object_or_404(Lease, pk=pk)

    if lease.tenant:
        messages.error(request, "This lease already has a tenant assigned.")
        return redirect("leases_admin:lease_detail", pk=pk)

    if not lease.prospective_email:
        messages.error(
            request,
            "Cannot start onboarding: No email address for prospective tenant. "
            "Please edit the lease and add a prospective email."
        )
        return redirect("leases_admin:lease_detail", pk=pk)

    # Check if there's already an active onboarding session for this lease
    from apps.tenant_lifecycle.models import OnboardingSession
    existing_session = OnboardingSession.objects.filter(
        lease=lease,
        status__in=["pending", "in_progress"],
    ).first()

    if existing_session:
        messages.warning(
            request,
            "An onboarding session already exists for this lease. "
            "Redirecting to the existing session."
        )
        return redirect("tenant_lifecycle_admin:admin_session_detail", pk=existing_session.pk)

    if request.method == "POST":
        from apps.tenant_lifecycle.services import OnboardingService

        try:
            session = OnboardingService.create_session(
                unit=lease.unit,
                prospective_email=lease.prospective_email,
                prospective_first_name=lease.prospective_first_name,
                prospective_last_name=lease.prospective_last_name,
                prospective_phone=lease.prospective_phone,
                lease=lease,
                created_by=request.user,
                send_invitation=True,
            )
            messages.success(
                request,
                f"Onboarding invitation sent to {lease.prospective_email}. "
                "The tenant will receive an email with instructions to complete onboarding."
            )
            return redirect("tenant_lifecycle_admin:admin_session_detail", pk=session.pk)
        except Exception as e:
            messages.error(request, f"Failed to create onboarding session: {e}")
            return redirect("leases_admin:lease_detail", pk=pk)

    # GET - show confirmation page
    return render(request, "leases/admin_lease_start_onboarding.html", {"lease": lease})


# =============================================================================
# Tenant Views
# =============================================================================

@tenant_required
def tenant_lease_list(request):
    """Show all leases for the tenant (current and past)."""
    leases = Lease.objects.filter(
        tenant=request.user
    ).select_related("unit", "unit__property").order_by("-start_date")

    current_lease = leases.filter(status__in=["active", "renewed"]).first()
    past_leases = leases.exclude(status__in=["active", "renewed", "draft"])

    return render(request, "leases/tenant_lease_list.html", {
        "current_lease": current_lease,
        "past_leases": past_leases,
    })


@tenant_required
def tenant_lease_detail(request, pk=None):
    """Show detailed lease information for a tenant."""
    if pk:
        lease = get_object_or_404(
            Lease.objects.select_related("unit", "unit__property")
            .prefetch_related("terms", "occupants", "pets", "fees", "documents", "signatures"),
            pk=pk,
            tenant=request.user,
        )
    else:
        # Default to active lease if no pk specified
        lease = Lease.objects.filter(
            tenant=request.user, status__in=["active", "renewed"]
        ).select_related("unit", "unit__property").prefetch_related(
            "terms", "occupants", "pets", "fees", "documents", "signatures"
        ).first()

    if not lease:
        return render(request, "leases/tenant_lease_detail.html", {"lease": None})

    # Get documents linked to this lease
    from apps.documents.models import Document, EDocument
    documents = Document.objects.filter(
        lease=lease, deleted_at__isnull=True, is_tenant_visible=True
    ).order_by("-created_at")
    edocuments = EDocument.objects.filter(
        lease=lease, status="completed"
    ).order_by("-completed_at")

    # Check if tenant has a pending signature
    pending_signature = LeaseSignature.objects.filter(
        lease=lease,
        signer_email=request.user.email,
        signed_at__isnull=True,
    ).first()

    # Check if tenant has already signed
    tenant_signature = LeaseSignature.objects.filter(
        lease=lease,
        signer_email=request.user.email,
        signed_at__isnull=False,
    ).first()

    return render(request, "leases/tenant_lease_detail.html", {
        "lease": lease,
        "terms": lease.terms.all(),
        "occupants": lease.occupants.all(),
        "pets": lease.pets.all(),
        "fees": lease.fees.all(),
        "documents": documents,
        "edocuments": edocuments,
        "pending_signature": pending_signature,
        "tenant_signature": tenant_signature,
    })


@tenant_required
@require_POST
def tenant_sign_lease(request, pk):
    """Allow tenant to sign their lease from the detail page."""
    lease = get_object_or_404(Lease, pk=pk, tenant=request.user)

    # Find tenant's pending signature record
    signature = LeaseSignature.objects.filter(
        lease=lease,
        signer_email=request.user.email,
        signed_at__isnull=True,
    ).first()

    if not signature:
        messages.error(request, "No pending signature found for this lease.")
        return redirect("leases_tenant:lease_detail")

    # Validate form data
    typed_name = request.POST.get("typed_name", "").strip()
    signature_data = request.POST.get("signature_data", "")
    agree_to_terms = request.POST.get("agree_to_terms")

    if not agree_to_terms:
        messages.error(request, "You must agree to the lease terms.")
        return redirect("leases_tenant:lease_detail_by_id", pk=pk)

    if not typed_name:
        messages.error(request, "Please type your full name to confirm.")
        return redirect("leases_tenant:lease_detail_by_id", pk=pk)

    if typed_name.lower() != signature.signer_name.lower():
        messages.error(request, f"Typed name must match '{signature.signer_name}'.")
        return redirect("leases_tenant:lease_detail_by_id", pk=pk)

    if not signature_data:
        messages.error(request, "Please draw your signature.")
        return redirect("leases_tenant:lease_detail_by_id", pk=pk)

    # Record signature
    signature.signature_image = signature_data
    signature.signed_at = timezone.now()
    signature.ip_address = get_client_ip(request)
    signature.user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
    signature.save()

    # Update lease status
    update_lease_signature_status(lease)

    messages.success(request, "Your signature has been recorded. Thank you!")
    return redirect("leases_tenant:lease_detail_by_id", pk=pk)


# =============================================================================
# Admin Signature Workflow Views
# =============================================================================

def update_lease_signature_status(lease):
    """Update lease signature_status based on collected signatures."""
    signatures = lease.signatures.all()
    total = signatures.count()
    signed = signatures.filter(signed_at__isnull=False).count()

    if total == 0:
        return

    if signed == total:
        lease.signature_status = "executed"
        lease.fully_executed_at = timezone.now()
    elif signed > 0:
        lease.signature_status = "partial"

    lease.save(update_fields=["signature_status", "fully_executed_at"])


@admin_required
@require_POST
def admin_mark_lease_signed(request, pk):
    """Manually mark a lease as fully signed (for physical/external signatures)."""
    lease = get_object_or_404(Lease, pk=pk)

    if lease.signature_status == "executed":
        messages.info(request, "This lease is already marked as signed.")
        return redirect("leases_admin:lease_detail", pk=pk)

    lease.signature_status = "executed"
    lease.fully_executed_at = timezone.now()
    lease.save(update_fields=["signature_status", "fully_executed_at"])

    messages.success(request, "Lease has been marked as signed.")
    return redirect("leases_admin:lease_detail", pk=pk)


@admin_required
def admin_send_for_signature(request, pk):
    """Send a lease out for electronic signatures."""
    lease = get_object_or_404(Lease, pk=pk)

    if lease.signature_status not in ["draft"]:
        messages.error(request, "This lease has already been sent for signatures.")
        return redirect("leases_admin:lease_detail", pk=lease.pk)

    if request.method == "POST":
        # Create signature records for all required signers
        signers = []

        # Primary tenant
        if lease.tenant:
            signers.append({
                "signer_type": "tenant",
                "signer_name": lease.tenant.get_full_name() or lease.tenant.username,
                "signer_email": lease.tenant.email,
                "signer_user": lease.tenant,
            })

        # Occupants who are on lease or cosigners
        for occupant in lease.occupants.filter(is_on_lease=True):
            if occupant.email:
                signers.append({
                    "signer_type": "cosigner" if occupant.is_cosigner else "occupant",
                    "signer_name": f"{occupant.first_name} {occupant.last_name}",
                    "signer_email": occupant.email,
                    "signer_user": None,
                })

        # Create signature records
        from datetime import timedelta
        for signer in signers:
            token = secrets.token_urlsafe(32)
            LeaseSignature.objects.create(
                lease=lease,
                signer_type=signer["signer_type"],
                signer_name=signer["signer_name"],
                signer_email=signer["signer_email"],
                signer_user=signer.get("signer_user"),
                signing_token=token,
                token_expires_at=timezone.now() + timedelta(days=7),
            )

        # Update lease status
        lease.signature_status = "pending"
        lease.signature_requested_at = timezone.now()
        lease.save()

        # Send email notifications to signers with signing links
        from apps.core.services.email import send_email
        from django.urls import reverse

        email_count = 0
        for sig in lease.signatures.filter(signed_at__isnull=True):
            signing_url = request.build_absolute_uri(
                reverse("leases_signing:signing_page", kwargs={"token": sig.signing_token})
            )
            property_name = lease.unit.property.name if lease.unit else "your property"
            unit_number = lease.unit.unit_number if lease.unit else ""

            subject = f"Lease Signature Required - {property_name}"
            message = (
                f"Hello {sig.signer_name},\n\n"
                f"You have been requested to sign the lease agreement for:\n"
                f"Property: {property_name}\n"
                f"Unit: {unit_number}\n\n"
                f"Please click the link below to review and sign the lease:\n"
                f"{signing_url}\n\n"
                f"This link will expire in 7 days.\n\n"
                f"If you have any questions, please contact your property manager.\n\n"
                f"Thank you,\nPropManager"
            )

            if send_email(
                subject=subject,
                message=message,
                recipient_list=[sig.signer_email],
                source="lease_signing",
            ):
                email_count += 1

        messages.success(
            request,
            f"Lease sent for signatures to {len(signers)} signer(s). "
            f"{email_count} email notification(s) sent."
        )
        return redirect("leases_admin:lease_detail", pk=lease.pk)

    # GET - show confirmation page
    return render(request, "leases/admin_send_for_signature.html", {"lease": lease})


# =============================================================================
# Public Signing Views (Token-Based, No Login Required)
# =============================================================================

def signing_page(request, token):
    """Public signing page accessible via unique token."""
    signature = get_object_or_404(
        LeaseSignature.objects.select_related(
            "lease", "lease__unit", "lease__unit__property", "lease__tenant"
        ).prefetch_related("lease__terms"),
        signing_token=token,
    )

    # Check if token is expired
    if signature.token_expires_at and signature.token_expires_at < timezone.now():
        return render(request, "leases/signing_expired.html", {"signature": signature})

    # Check if already signed
    if signature.signed_at:
        return render(request, "leases/signing_complete.html", {"signature": signature})

    lease = signature.lease
    form = SignLeaseForm()

    return render(request, "leases/signing_page.html", {
        "signature": signature,
        "lease": lease,
        "terms": lease.terms.all(),
        "form": form,
    })


@require_POST
def submit_signature(request, token):
    """Process signature submission."""
    signature = get_object_or_404(LeaseSignature, signing_token=token)

    # Validate token
    if signature.token_expires_at and signature.token_expires_at < timezone.now():
        return JsonResponse({"error": "Signing link has expired."}, status=400)

    if signature.signed_at:
        return JsonResponse({"error": "This lease has already been signed."}, status=400)

    form = SignLeaseForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"error": "Please complete all required fields."}, status=400)

    # Verify typed name matches
    typed_name = form.cleaned_data["typed_name"]
    if typed_name.lower().strip() != signature.signer_name.lower().strip():
        return JsonResponse({
            "error": f"Typed name must match '{signature.signer_name}'."
        }, status=400)

    # Save signature
    signature.signature_image = form.cleaned_data["signature_data"]
    signature.signed_at = timezone.now()
    signature.ip_address = get_client_ip(request)
    signature.user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
    signature.save()

    # Check if all signatures are collected
    lease = signature.lease
    unsigned_count = lease.signatures.filter(signed_at__isnull=True).count()

    if unsigned_count == 0:
        # All signatures collected - mark lease as fully executed
        lease.signature_status = "executed"
        lease.fully_executed_at = timezone.now()
        lease.save()

        # Notify all parties that the lease is fully signed
        from apps.core.services.email import send_email
        property_name = lease.unit.property.name if lease.unit else "your property"
        unit_number = lease.unit.unit_number if lease.unit else ""

        for sig in lease.signatures.all():
            subject = f"Lease Fully Executed - {property_name}"
            message = (
                f"Hello {sig.signer_name},\n\n"
                f"Great news! All signatures have been collected and the lease agreement "
                f"for {property_name} (Unit {unit_number}) is now fully executed.\n\n"
                f"Signed on: {lease.fully_executed_at.strftime('%B %d, %Y')}\n\n"
                f"Please keep this email for your records. A copy of the signed lease "
                f"will be available in your tenant portal.\n\n"
                f"Thank you,\nPropManager"
            )
            send_email(
                subject=subject,
                message=message,
                recipient_list=[sig.signer_email],
                source="lease_completion",
            )
    else:
        # Still waiting on signatures
        lease.signature_status = "partial"
        lease.save()

    return JsonResponse({
        "success": True,
        "message": "Your signature has been recorded. Thank you!",
        "redirect": request.build_absolute_uri(
            f"/lease/sign/{token}/"
        ),
    })


def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
