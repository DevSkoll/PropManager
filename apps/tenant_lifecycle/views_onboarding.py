"""
Public onboarding views for tenant self-service.

Provides the multi-step wizard flow for tenant onboarding:
1. Account creation (OTP verification)
2. Information collection (personal info, contacts, occupants, pets, vehicles, employment)
3. Document signing
4. Fee review (acknowledgment)
5. Welcome/completion
"""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.leases.models import LeaseOccupant, LeasePet

from .decorators import get_client_ip, log_step_access, onboarding_token_required
from .forms import (
    AccountCreationForm,
    EmergencyContactForm,
    EmploymentForm,
    IDVerificationForm,
    InsuranceForm,
    InsuranceWaiverForm,
    MoveInScheduleForm,
    OccupantForm,
    OTPVerificationForm,
    PersonalInfoForm,
    PetForm,
    VehicleForm,
)
from .models import (
    OnboardingDocument,
    OnboardingPayment,
    OnboardingSession,
    TenantEmergencyContact,
    TenantEmployment,
    TenantIDVerification,
    TenantInsurance,
    TenantVehicle,
)
from .services import OnboardingService


# =============================================================================
# Entry Point & Routing
# =============================================================================


@onboarding_token_required
def onboarding_start(request, token):
    """
    Entry point for onboarding.

    Redirects to the appropriate step based on session state.
    """
    session = request.onboarding_session

    # If no tenant account yet, start with account creation
    if not session.tenant:
        return redirect("tenant_lifecycle:onboarding_verify", token=token)

    # Otherwise, route to current step
    next_step = session.get_next_step()
    if not next_step:
        return redirect("tenant_lifecycle:onboarding_complete", token=token)

    return redirect(f"tenant_lifecycle:onboarding_{next_step}", token=token)


@onboarding_token_required
def onboarding_router(request, token):
    """
    Route to the next incomplete step.

    Used after completing a step to automatically move forward.
    """
    session = request.onboarding_session
    next_step = session.get_next_step()

    if not next_step:
        return redirect("tenant_lifecycle:onboarding_complete", token=token)

    return redirect(f"tenant_lifecycle:onboarding_{next_step}", token=token)


# =============================================================================
# Account Creation Steps
# =============================================================================


@onboarding_token_required
def onboarding_verify(request, token):
    """
    Step 1a: Verify email and send OTP.

    Shows email confirmation and sends OTP code.
    """
    from django.conf import settings

    session = request.onboarding_session

    # If already verified, skip
    if session.tenant:
        return redirect("tenant_lifecycle:onboarding_router", token=token)

    if request.method == "POST":
        # Generate OTP code
        otp_code = session.generate_otp()

        # In production, send email with OTP
        if not settings.DEBUG:
            from apps.core.services.email import send_email
            send_email(
                subject="Your Verification Code",
                message=f"Your verification code is: {otp_code}\n\nThis code expires in 10 minutes.",
                recipient_list=[session.prospective_email],
                source="onboarding_otp",
            )
            messages.success(request, "Verification code sent to your email.")
        else:
            # In dev mode, show the code in the message
            messages.success(request, f"Dev mode - your code is: {otp_code}")

        return redirect("tenant_lifecycle:onboarding_otp", token=token)

    context = {
        "session": session,
        "email": session.prospective_email,
    }
    return render(request, "tenant_lifecycle/onboarding/verify.html", context)


@onboarding_token_required
def onboarding_otp(request, token):
    """
    Step 1b: Enter OTP code.
    """
    session = request.onboarding_session

    if session.tenant:
        return redirect("tenant_lifecycle:onboarding_router", token=token)

    if request.method == "POST":
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["otp_code"]

            # Verify OTP using session method
            if session.verify_otp(code):
                # Clear the OTP after successful verification
                session.otp_code = ""
                session.otp_expires_at = None
                session.save(update_fields=["otp_code", "otp_expires_at", "updated_at"])

                # Store verification in session (Django session)
                request.session["onboarding_verified"] = True
                request.session["onboarding_email"] = session.prospective_email
                return redirect("tenant_lifecycle:onboarding_account_creation", token=token)
            else:
                form.add_error("otp_code", "Invalid or expired code. Please try again.")
    else:
        form = OTPVerificationForm()

    context = {
        "session": session,
        "form": form,
    }
    return render(request, "tenant_lifecycle/onboarding/otp.html", context)


@onboarding_token_required
def onboarding_create_account(request, token):
    """
    Step 1c: Create account with name and contact preferences.
    """
    session = request.onboarding_session

    # Check OTP verification
    if not request.session.get("onboarding_verified"):
        return redirect("tenant_lifecycle:onboarding_verify", token=token)

    if session.tenant:
        return redirect("tenant_lifecycle:onboarding_router", token=token)

    if request.method == "POST":
        form = AccountCreationForm(request.POST)
        if form.is_valid():
            # Create account
            user = OnboardingService.create_tenant_account(
                session=session,
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                phone_number=form.cleaned_data.get("phone_number", ""),
                preferred_contact=form.cleaned_data["preferred_contact"],
            )

            # Log in the user with default backend
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")

            # Mark step complete
            session.mark_step_complete("account_creation")

            # Clear OTP session data
            request.session.pop("onboarding_verified", None)
            request.session.pop("onboarding_email", None)

            messages.success(request, "Account created successfully!")
            return redirect("tenant_lifecycle:onboarding_router", token=token)
    else:
        form = AccountCreationForm(initial={
            "first_name": session.prospective_first_name,
            "last_name": session.prospective_last_name,
            "phone_number": session.prospective_phone,
        })

    context = {
        "session": session,
        "form": form,
    }
    return render(request, "tenant_lifecycle/onboarding/create_account.html", context)


# =============================================================================
# Information Collection Steps
# =============================================================================


@onboarding_token_required
def onboarding_personal_info(request, token):
    """Step 2: Personal information."""
    session = request.onboarding_session
    log_step_access(session, "personal_info", request)

    if request.method == "POST":
        form = PersonalInfoForm(request.POST)
        if form.is_valid():
            # Store personal info in session.collected_data
            session.collected_data["personal_info"] = {
                "date_of_birth": form.cleaned_data["date_of_birth"].isoformat() if form.cleaned_data.get("date_of_birth") else None,
                "ssn_last_four": form.cleaned_data.get("ssn_last_four", ""),
                "drivers_license_state": form.cleaned_data.get("drivers_license_state", ""),
                "drivers_license_number": form.cleaned_data.get("drivers_license_number", ""),
            }
            session.save(update_fields=["collected_data"])

            session.mark_step_complete("personal_info")
            return redirect("tenant_lifecycle:onboarding_router", token=token)
    else:
        # Pre-populate from existing data if available
        initial = {}
        if session.collected_data.get("personal_info"):
            pi = session.collected_data["personal_info"]
            initial = {
                "date_of_birth": pi.get("date_of_birth"),
                "ssn_last_four": pi.get("ssn_last_four", ""),
                "drivers_license_state": pi.get("drivers_license_state", ""),
                "drivers_license_number": pi.get("drivers_license_number", ""),
            }
        form = PersonalInfoForm(initial=initial)

    context = {
        "session": session,
        "form": form,
        "step_name": "Personal Information",
    }
    return render(request, "tenant_lifecycle/onboarding/personal_info.html", context)


@onboarding_token_required
def onboarding_emergency_contacts(request, token):
    """Step 3: Emergency contacts."""
    session = request.onboarding_session
    log_step_access(session, "emergency_contacts", request)

    # Get existing contacts
    existing_contacts = list(TenantEmergencyContact.objects.filter(
        onboarding_session=session
    ))

    if request.method == "POST":
        form = EmergencyContactForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.tenant = session.tenant
            contact.lease = session.lease
            contact.onboarding_session = session
            contact.save()
            messages.success(request, "Emergency contact added.")

            return redirect("tenant_lifecycle:onboarding_emergency_contacts", token=token)
    else:
        form = EmergencyContactForm()

    context = {
        "session": session,
        "form": form,
        "contacts": existing_contacts,
        "step_name": "Emergency Contacts",
        "can_continue": len(existing_contacts) > 0,
    }
    return render(request, "tenant_lifecycle/onboarding/emergency_contacts.html", context)


@onboarding_token_required
@require_POST
def onboarding_emergency_contacts_complete(request, token):
    """Mark emergency contacts step as complete."""
    session = request.onboarding_session

    # Verify at least one contact
    count = TenantEmergencyContact.objects.filter(onboarding_session=session).count()
    if count == 0:
        messages.error(request, "Please add at least one emergency contact.")
        return redirect("tenant_lifecycle:onboarding_emergency_contacts", token=token)

    session.mark_step_complete("emergency_contacts")
    return redirect("tenant_lifecycle:onboarding_router", token=token)


@onboarding_token_required
def onboarding_occupants(request, token):
    """Step 4: Occupants/household members."""
    session = request.onboarding_session
    log_step_access(session, "occupants", request)

    # Get existing occupants from lease
    existing_occupants = list(LeaseOccupant.objects.filter(lease=session.lease))

    if request.method == "POST":
        form = OccupantForm(request.POST)
        if form.is_valid():
            occupant = form.save(commit=False)
            occupant.lease = session.lease
            occupant.save()
            messages.success(request, "Occupant added.")
            return redirect("tenant_lifecycle:onboarding_occupants", token=token)
    else:
        form = OccupantForm()

    context = {
        "session": session,
        "form": form,
        "occupants": existing_occupants,
        "step_name": "Household Members",
    }
    return render(request, "tenant_lifecycle/onboarding/occupants.html", context)


@onboarding_token_required
@require_POST
def onboarding_occupants_complete(request, token):
    """Mark occupants step as complete."""
    session = request.onboarding_session
    session.mark_step_complete("occupants")
    return redirect("tenant_lifecycle:onboarding_router", token=token)


@onboarding_token_required
def onboarding_pets(request, token):
    """Step 5: Pet registration."""
    session = request.onboarding_session
    log_step_access(session, "pets", request)

    # Get existing pets from lease
    existing_pets = list(LeasePet.objects.filter(lease=session.lease))

    if request.method == "POST":
        form = PetForm(request.POST)
        if form.is_valid():
            pet = form.save(commit=False)
            pet.lease = session.lease
            pet.save()
            messages.success(request, "Pet registered.")
            return redirect("tenant_lifecycle:onboarding_pets", token=token)
    else:
        form = PetForm()

    context = {
        "session": session,
        "form": form,
        "pets": existing_pets,
        "step_name": "Pet Registration",
    }
    return render(request, "tenant_lifecycle/onboarding/pets.html", context)


@onboarding_token_required
@require_POST
def onboarding_pets_complete(request, token):
    """Mark pets step as complete."""
    session = request.onboarding_session
    session.mark_step_complete("pets")
    return redirect("tenant_lifecycle:onboarding_router", token=token)


@onboarding_token_required
def onboarding_vehicles(request, token):
    """Step 6: Vehicle registration."""
    session = request.onboarding_session
    log_step_access(session, "vehicles", request)

    existing_vehicles = list(TenantVehicle.objects.filter(
        onboarding_session=session
    ))

    if request.method == "POST":
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.tenant = session.tenant
            vehicle.lease = session.lease
            vehicle.onboarding_session = session
            vehicle.save()
            messages.success(request, "Vehicle registered.")
            return redirect("tenant_lifecycle:onboarding_vehicles", token=token)
    else:
        form = VehicleForm()

    context = {
        "session": session,
        "form": form,
        "vehicles": existing_vehicles,
        "step_name": "Vehicle Registration",
    }
    return render(request, "tenant_lifecycle/onboarding/vehicles.html", context)


@onboarding_token_required
@require_POST
def onboarding_vehicles_complete(request, token):
    """Mark vehicles step as complete."""
    session = request.onboarding_session
    session.mark_step_complete("vehicles")
    return redirect("tenant_lifecycle:onboarding_router", token=token)


@onboarding_token_required
def onboarding_employment(request, token):
    """Step 7: Employment information."""
    session = request.onboarding_session
    log_step_access(session, "employment", request)

    existing = TenantEmployment.objects.filter(
        onboarding_session=session, is_current=True
    ).first()

    if request.method == "POST":
        form = EmploymentForm(request.POST, instance=existing)
        if form.is_valid():
            employment = form.save(commit=False)
            employment.tenant = session.tenant
            employment.lease = session.lease
            employment.onboarding_session = session
            employment.is_current = True
            employment.save()

            session.mark_step_complete("employment")
            return redirect("tenant_lifecycle:onboarding_router", token=token)
    else:
        form = EmploymentForm(instance=existing)

    context = {
        "session": session,
        "form": form,
        "step_name": "Employment & Income",
    }
    return render(request, "tenant_lifecycle/onboarding/employment.html", context)


@onboarding_token_required
def onboarding_insurance(request, token):
    """Step 8: Renter's insurance."""
    session = request.onboarding_session
    log_step_access(session, "insurance", request)

    existing = TenantInsurance.objects.filter(
        onboarding_session=session
    ).first()

    template = session.template
    is_required = template.require_renters_insurance if template else False

    if request.method == "POST":
        if "waive" in request.POST and not is_required:
            # Waiving insurance
            waiver_form = InsuranceWaiverForm(request.POST)
            if waiver_form.is_valid():
                session.mark_step_complete("insurance")
                return redirect("tenant_lifecycle:onboarding_router", token=token)
        else:
            form = InsuranceForm(request.POST, request.FILES, instance=existing)
            if form.is_valid():
                insurance = form.save(commit=False)
                insurance.tenant = session.tenant
                insurance.lease = session.lease
                insurance.onboarding_session = session
                insurance.save()

                session.mark_step_complete("insurance")
                return redirect("tenant_lifecycle:onboarding_router", token=token)
    else:
        form = InsuranceForm(instance=existing)

    waiver_form = InsuranceWaiverForm() if not is_required else None

    context = {
        "session": session,
        "form": form,
        "waiver_form": waiver_form,
        "is_required": is_required,
        "step_name": "Renter's Insurance",
    }
    return render(request, "tenant_lifecycle/onboarding/insurance.html", context)


@onboarding_token_required
def onboarding_id_verification(request, token):
    """Step 9: ID verification upload."""
    session = request.onboarding_session
    log_step_access(session, "id_verification", request)

    existing = TenantIDVerification.objects.filter(
        onboarding_session=session
    ).first()

    if request.method == "POST":
        form = IDVerificationForm(request.POST, request.FILES, instance=existing)
        if form.is_valid():
            verification = form.save(commit=False)
            verification.tenant = session.tenant
            verification.lease = session.lease
            verification.onboarding_session = session
            verification.status = "pending"
            verification.save()

            session.mark_step_complete("id_verification")
            return redirect("tenant_lifecycle:onboarding_router", token=token)
    else:
        form = IDVerificationForm(instance=existing)

    context = {
        "session": session,
        "form": form,
        "step_name": "ID Verification",
    }
    return render(request, "tenant_lifecycle/onboarding/id_verification.html", context)


# =============================================================================
# Document Signing Steps
# =============================================================================


@onboarding_token_required
def onboarding_documents(request, token):
    """Step 10: Document signing overview."""
    session = request.onboarding_session
    log_step_access(session, "documents", request)

    # Create documents if not already created
    OnboardingService.create_session_documents(session)

    documents = OnboardingDocument.objects.filter(session=session).select_related(
        "edocument", "template_document"
    )

    # Check if all required documents are signed
    all_signed = OnboardingService.check_documents_complete(session)

    context = {
        "session": session,
        "documents": documents,
        "all_signed": all_signed,
        "step_name": "Document Signing",
    }
    return render(request, "tenant_lifecycle/onboarding/documents.html", context)


@onboarding_token_required
@require_POST
def onboarding_documents_complete(request, token):
    """Mark documents step as complete."""
    session = request.onboarding_session

    if not OnboardingService.check_documents_complete(session):
        messages.error(request, "Please sign all required documents.")
        return redirect("tenant_lifecycle:onboarding_documents", token=token)

    session.mark_step_complete("documents")
    return redirect("tenant_lifecycle:onboarding_router", token=token)


@onboarding_token_required
def onboarding_sign_document(request, token, doc_pk):
    """Sign a specific document."""
    session = request.onboarding_session

    ob_doc = get_object_or_404(
        OnboardingDocument.objects.select_related("edocument"),
        pk=doc_pk,
        session=session,
    )

    if not ob_doc.edocument:
        raise Http404("Document not found.")

    # Mark as viewed
    if not ob_doc.viewed_at:
        ob_doc.viewed_at = timezone.now()
        ob_doc.save(update_fields=["viewed_at", "updated_at"])

    # Redirect to the eDocument signing view
    from django.urls import reverse
    edoc_sign_url = reverse(
        "documents_tenant:edoc_detail",
        kwargs={"pk": ob_doc.edocument.pk}
    )

    return redirect(edoc_sign_url)


# =============================================================================
# Payment Steps
# =============================================================================


@onboarding_token_required
def onboarding_payments(request, token):
    """Step 11: Review move-in fees (acknowledgment only, no payment)."""
    session = request.onboarding_session
    log_step_access(session, "payments", request)

    # Get fees from template (display only - no payment processing)
    fees = []
    total_due = Decimal("0.00")
    if session.template:
        for fee in session.template.fees.filter(is_required=True):
            amount = fee.get_amount_for_lease(session.lease)
            fees.append({
                "name": fee.name,
                "description": fee.description,
                "amount": amount,
                "fee_type": fee.get_fee_type_display(),
                "is_refundable": fee.is_refundable,
            })
            total_due += amount

    context = {
        "session": session,
        "fees": fees,
        "total_due": total_due,
        "step_name": "Review Move-In Fees",
    }
    return render(request, "tenant_lifecycle/onboarding/review_fees.html", context)


@onboarding_token_required
@require_POST
def onboarding_payments_complete(request, token):
    """Acknowledge fees and mark step complete."""
    session = request.onboarding_session

    # Verify acknowledgment checkbox was checked
    if not request.POST.get("acknowledge_fees"):
        messages.error(request, "Please acknowledge the fees to continue.")
        return redirect("tenant_lifecycle:onboarding_payments", token=token)

    session.mark_step_complete("payments")
    return redirect("tenant_lifecycle:onboarding_router", token=token)


# =============================================================================
# Final Steps
# =============================================================================


@onboarding_token_required
def onboarding_move_in_schedule(request, token):
    """Step 12: Move-in scheduling."""
    session = request.onboarding_session
    log_step_access(session, "move_in_schedule", request)

    if request.method == "POST":
        form = MoveInScheduleForm(request.POST)
        if form.is_valid():
            # Store move-in preferences
            session.steps_completed["move_in_schedule_data"] = {
                "date": form.cleaned_data["move_in_date"].isoformat(),
                "time": form.cleaned_data["preferred_time"],
                "requests": form.cleaned_data.get("special_requests", ""),
            }
            session.save(update_fields=["steps_completed", "updated_at"])

            session.mark_step_complete("move_in_schedule")
            return redirect("tenant_lifecycle:onboarding_router", token=token)
    else:
        form = MoveInScheduleForm()

        # Pre-populate if lease has start date
        if session.lease and session.lease.start_date:
            form = MoveInScheduleForm(initial={
                "move_in_date": session.lease.start_date,
            })

    context = {
        "session": session,
        "form": form,
        "step_name": "Move-In Schedule",
    }
    return render(request, "tenant_lifecycle/onboarding/move_in_schedule.html", context)


@onboarding_token_required
def onboarding_welcome(request, token):
    """Step 13: Welcome and property information."""
    session = request.onboarding_session
    log_step_access(session, "welcome", request)

    template = session.template
    property_obj = session.unit.property if session.unit else None

    # Get checklist items
    checklist = template.move_in_checklist if template else []

    context = {
        "session": session,
        "template": template,
        "property": property_obj,
        "welcome_message": template.welcome_message if template else "",
        "property_rules": template.property_rules if template else "",
        "checklist": checklist,
        "step_name": "Welcome!",
    }
    return render(request, "tenant_lifecycle/onboarding/welcome.html", context)


@onboarding_token_required
@require_POST
def onboarding_welcome_complete(request, token):
    """Complete onboarding."""
    session = request.onboarding_session

    session.mark_step_complete("welcome")

    # Finalize the session
    OnboardingService.complete_session(session)

    return redirect("tenant_lifecycle:onboarding_complete", token=token)


@onboarding_token_required
def onboarding_complete(request, token):
    """Completion page."""
    session = request.onboarding_session

    context = {
        "session": session,
    }
    return render(request, "tenant_lifecycle/onboarding/complete.html", context)


# =============================================================================
# AJAX Endpoints for Dynamic Forms
# =============================================================================


@onboarding_token_required
@require_POST
def api_delete_occupant(request, token, pk):
    """Delete an occupant (AJAX)."""
    session = request.onboarding_session

    occupant = get_object_or_404(LeaseOccupant, pk=pk, lease=session.lease)
    occupant.delete()

    return JsonResponse({"success": True})


@onboarding_token_required
@require_POST
def api_delete_pet(request, token, pk):
    """Delete a pet (AJAX)."""
    session = request.onboarding_session

    pet = get_object_or_404(LeasePet, pk=pk, lease=session.lease)
    pet.delete()

    return JsonResponse({"success": True})


@onboarding_token_required
@require_POST
def api_delete_vehicle(request, token, pk):
    """Delete a vehicle (AJAX)."""
    session = request.onboarding_session

    vehicle = get_object_or_404(
        TenantVehicle, pk=pk, onboarding_session=session
    )
    vehicle.delete()

    return JsonResponse({"success": True})


@onboarding_token_required
@require_POST
def api_delete_contact(request, token, pk):
    """Delete an emergency contact (AJAX)."""
    session = request.onboarding_session

    contact = get_object_or_404(
        TenantEmergencyContact, pk=pk, onboarding_session=session
    )
    contact.delete()

    return JsonResponse({"success": True})
