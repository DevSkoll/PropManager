"""
Tenant management services.

Provides functions for:
- Checking if a tenant can be deleted
- Deleting tenants (with cleanup)
- Archiving and restoring tenants
"""

from django.utils import timezone


def can_delete_tenant(user):
    """
    Check if a tenant can be safely deleted.

    Returns False if tenant has:
    - Active or any leases (PROTECT constraint)
    - Payments on record (PROTECT constraint)
    - Active/overdue invoices

    These constraints prevent deletion to preserve business data integrity.
    """
    # Check for any leases (PROTECT)
    if user.leases.exists():
        return False

    # Check for any payments (PROTECT)
    if user.payments.exists():
        return False

    # Check for unpaid invoices
    if user.invoices.filter(status__in=["pending", "issued", "overdue", "partial"]).exists():
        return False

    return True


def get_delete_blockers(user):
    """
    Get a list of reasons preventing tenant deletion.

    Returns a list of human-readable strings explaining why
    the tenant cannot be deleted.
    """
    blockers = []

    # Check leases
    lease_count = user.leases.count()
    if lease_count:
        blockers.append(f"{lease_count} lease{'s' if lease_count != 1 else ''} linked")

    # Check payments
    payment_count = user.payments.count()
    if payment_count:
        blockers.append(f"{payment_count} payment record{'s' if payment_count != 1 else ''}")

    # Check unpaid invoices
    unpaid_count = user.invoices.filter(
        status__in=["pending", "issued", "overdue", "partial"]
    ).count()
    if unpaid_count:
        blockers.append(f"{unpaid_count} unpaid invoice{'s' if unpaid_count != 1 else ''}")

    return blockers


def get_delete_summary(user):
    """
    Get summary of what will be deleted when deleting a tenant.

    Returns a dict with counts of related records that will be removed.
    """
    summary = {}

    # Profile
    if hasattr(user, "tenant_profile"):
        summary["profile"] = True

    # Emergency contacts
    if hasattr(user, "emergency_contacts"):
        count = user.emergency_contacts.count()
        if count:
            summary["emergency_contacts"] = count

    # Vehicles
    if hasattr(user, "vehicles"):
        count = user.vehicles.count()
        if count:
            summary["vehicles"] = count

    # Employment records
    if hasattr(user, "employments"):
        count = user.employments.count()
        if count:
            summary["employment_records"] = count

    # Insurance records
    if hasattr(user, "insurance_policies"):
        count = user.insurance_policies.count()
        if count:
            summary["insurance_policies"] = count

    # ID verifications
    if hasattr(user, "id_verifications"):
        count = user.id_verifications.count()
        if count:
            summary["id_verifications"] = count

    # Onboarding sessions
    if hasattr(user, "onboarding_sessions"):
        count = user.onboarding_sessions.count()
        if count:
            summary["onboarding_sessions"] = count

    # OTP tokens
    count = user.otp_tokens.count()
    if count:
        summary["otp_tokens"] = count

    # Notifications
    if hasattr(user, "notifications"):
        count = user.notifications.count()
        if count:
            summary["notifications"] = count

    return summary


def delete_tenant(user, deleted_by=None):
    """
    Delete a tenant and clean up related data.

    This function handles:
    1. SET_NULL cleanup for documents (preserve document but null out tenant)
    2. User deletion (CASCADE handles most relations)

    Args:
        user: The User instance to delete
        deleted_by: Optional user who performed the deletion (for audit)

    Returns:
        dict with deletion summary
    """
    summary = get_delete_summary(user)

    # Pre-delete cleanup for SET_NULL fields that should be explicitly nulled
    # EDocuments - preserve the document but remove tenant reference
    if hasattr(user, "edocuments_received"):
        user.edocuments_received.update(tenant=None)

    # Work orders - reported_by will be SET_NULL automatically
    # Documents - tenant will be SET_NULL automatically
    # Messages - sender will be SET_NULL automatically

    # Store name before deletion
    name = user.get_full_name() or user.email

    # Delete user (CASCADE handles most relations)
    user.delete()

    return {
        "name": name,
        "deleted_items": summary,
    }


def archive_tenant(user):
    """
    Archive a tenant by deactivating their account.

    Archived tenants:
    - Cannot log in
    - Are hidden from default tenant list
    - Preserve all historical data (leases, payments, etc.)
    - Can be restored later

    Args:
        user: The User instance to archive
    """
    user.is_active = False
    user.save(update_fields=["is_active"])


def restore_tenant(user):
    """
    Restore an archived tenant.

    Args:
        user: The User instance to restore
    """
    user.is_active = True
    user.save(update_fields=["is_active"])
