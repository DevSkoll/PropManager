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
        .prefetch_related("terms", "occupants", "pets", "fees", "signatures"),
        pk=pk
    )
    return render(request, "leases/admin_lease_detail.html", {
        "lease": lease,
        "terms": lease.terms.all(),
        "occupants": lease.occupants.all(),
        "pets": lease.pets.all(),
        "fees": lease.fees.all(),
        "signatures": lease.signatures.all(),
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
            .prefetch_related("terms", "occupants", "pets", "fees", "documents"),
            pk=pk,
            tenant=request.user,
        )
    else:
        # Default to active lease if no pk specified
        lease = Lease.objects.filter(
            tenant=request.user, status__in=["active", "renewed"]
        ).select_related("unit", "unit__property").prefetch_related(
            "terms", "occupants", "pets", "fees", "documents"
        ).first()

    if not lease:
        return render(request, "leases/tenant_lease_detail.html", {"lease": None})

    # Get documents linked to this lease
    from apps.documents.models import Document
    documents = Document.objects.filter(
        lease=lease, deleted_at__isnull=True, is_tenant_visible=True
    ).order_by("-created_at")

    return render(request, "leases/tenant_lease_detail.html", {
        "lease": lease,
        "terms": lease.terms.all(),
        "occupants": lease.occupants.all(),
        "pets": lease.pets.all(),
        "fees": lease.fees.all(),
        "documents": documents,
    })


# =============================================================================
# Admin Signature Workflow Views
# =============================================================================

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

        # TODO: Send email notifications to signers with signing links

        messages.success(
            request,
            f"Lease sent for signatures to {len(signers)} signer(s). "
            "Email notifications will be sent with signing links."
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
        # TODO: Generate signed PDF and notify all parties
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
