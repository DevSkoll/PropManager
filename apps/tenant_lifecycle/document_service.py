"""
Document service for onboarding file integration.

Creates Document records in the tenant's Documents section for
files uploaded during the onboarding process. Documents are stored
in an "Onboarding" folder scoped to the unit.
"""

import logging
import mimetypes

from apps.documents.models import Document, DocumentFolder

logger = logging.getLogger(__name__)

ONBOARDING_FOLDER_NAME = "Onboarding"


def get_or_create_onboarding_folder(unit, lease=None, created_by=None):
    """
    Get or create the "Onboarding" folder for a unit.

    Args:
        unit: Unit instance
        lease: Optional Lease to associate
        created_by: User who created the folder

    Returns:
        DocumentFolder instance
    """
    folder, created = DocumentFolder.objects.get_or_create(
        name=ONBOARDING_FOLDER_NAME,
        unit=unit,
        defaults={
            "description": "Documents uploaded during tenant onboarding",
            "lease": lease,
            "is_tenant_visible": True,
            "created_by": created_by,
        },
    )

    if created:
        logger.info("Created Onboarding folder for unit %s", unit)

    return folder


def create_document_from_insurance(insurance, created_by=None):
    """
    Create a Document record from a TenantInsurance policy document.

    Args:
        insurance: TenantInsurance instance with policy_document
        created_by: User who created the document

    Returns:
        Document instance or None if no file
    """
    if not insurance.policy_document:
        return None

    session = insurance.onboarding_session
    unit = session.unit if session else (insurance.lease.unit if insurance.lease else None)

    if not unit:
        logger.warning("Cannot create document for insurance %s: no unit found", insurance.pk)
        return None

    folder = get_or_create_onboarding_folder(
        unit=unit,
        lease=insurance.lease,
        created_by=created_by,
    )

    # Check for existing document (idempotent)
    existing = Document.objects.filter(
        folder=folder,
        tenant=insurance.tenant,
        file=insurance.policy_document.name,
    ).first()

    if existing:
        return existing

    # Get file info
    file_path = insurance.policy_document.name
    try:
        file_size = insurance.policy_document.size
    except (OSError, ValueError):
        file_size = 0
    mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

    document = Document.objects.create(
        title=f"Insurance Policy - {insurance.provider_name}",
        document_type="insurance",
        file=file_path,
        file_size=file_size,
        mime_type=mime_type,
        folder=folder,
        unit=unit,
        lease=insurance.lease,
        tenant=insurance.tenant,
        is_tenant_visible=True,
        uploaded_by_role="tenant",
        description=f"Policy #{insurance.policy_number}, Valid: {insurance.start_date} to {insurance.end_date}",
        created_by=created_by or insurance.tenant,
    )

    logger.info("Created Document %s from insurance %s", document.pk, insurance.pk)
    return document


def create_documents_from_id_verification(verification, created_by=None):
    """
    Create Document records from ID verification images.

    Args:
        verification: TenantIDVerification instance
        created_by: User who created the documents

    Returns:
        list of Document instances
    """
    created_docs = []

    session = verification.onboarding_session
    unit = session.unit if session else (verification.lease.unit if verification.lease else None)

    if not unit:
        logger.warning("Cannot create documents for ID verification %s: no unit found", verification.pk)
        return created_docs

    folder = get_or_create_onboarding_folder(
        unit=unit,
        lease=verification.lease,
        created_by=created_by,
    )

    id_type_display = verification.get_id_type_display()

    # Front image
    if verification.front_image:
        existing = Document.objects.filter(
            folder=folder,
            tenant=verification.tenant,
            file=verification.front_image.name,
        ).first()

        if not existing:
            try:
                file_size = verification.front_image.size
            except (OSError, ValueError):
                file_size = 0
            mime_type = mimetypes.guess_type(verification.front_image.name)[0] or "image/jpeg"

            doc = Document.objects.create(
                title=f"{id_type_display} - Front",
                document_type="photo",
                file=verification.front_image.name,
                file_size=file_size,
                mime_type=mime_type,
                folder=folder,
                unit=unit,
                lease=verification.lease,
                tenant=verification.tenant,
                is_tenant_visible=True,
                uploaded_by_role="tenant",
                description="ID verification document (front)",
                created_by=created_by or verification.tenant,
            )
            created_docs.append(doc)
            logger.info("Created Document %s from ID front image", doc.pk)
        else:
            created_docs.append(existing)

    # Back image
    if verification.back_image:
        existing = Document.objects.filter(
            folder=folder,
            tenant=verification.tenant,
            file=verification.back_image.name,
        ).first()

        if not existing:
            try:
                file_size = verification.back_image.size
            except (OSError, ValueError):
                file_size = 0
            mime_type = mimetypes.guess_type(verification.back_image.name)[0] or "image/jpeg"

            doc = Document.objects.create(
                title=f"{id_type_display} - Back",
                document_type="photo",
                file=verification.back_image.name,
                file_size=file_size,
                mime_type=mime_type,
                folder=folder,
                unit=unit,
                lease=verification.lease,
                tenant=verification.tenant,
                is_tenant_visible=True,
                uploaded_by_role="tenant",
                description="ID verification document (back)",
                created_by=created_by or verification.tenant,
            )
            created_docs.append(doc)
            logger.info("Created Document %s from ID back image", doc.pk)
        else:
            created_docs.append(existing)

    return created_docs


def create_document_from_edocument(edocument, created_by=None):
    """
    Create a Document record from a completed eDocument's final PDF.

    Args:
        edocument: EDocument instance with final_pdf
        created_by: User who created the document

    Returns:
        Document instance or None if no PDF or no unit
    """
    if not edocument.final_pdf:
        return None

    # Determine unit from lease
    unit = None
    if edocument.lease and edocument.lease.unit:
        unit = edocument.lease.unit

    if not unit:
        logger.warning("Cannot create document for eDocument %s: no unit found", edocument.pk)
        return None

    folder = get_or_create_onboarding_folder(
        unit=unit,
        lease=edocument.lease,
        created_by=created_by,
    )

    # Check for existing document (idempotent)
    existing = Document.objects.filter(
        folder=folder,
        file=edocument.final_pdf.name,
    ).first()

    if existing:
        return existing

    try:
        file_size = edocument.final_pdf.size
    except (OSError, ValueError):
        file_size = 0

    document = Document.objects.create(
        title=f"Signed: {edocument.title}",
        document_type="lease",
        file=edocument.final_pdf.name,
        file_size=file_size,
        mime_type="application/pdf",
        folder=folder,
        unit=unit,
        lease=edocument.lease,
        tenant=edocument.tenant,
        is_tenant_visible=True,
        uploaded_by_role="admin",
        description=f"Electronically signed document, completed {edocument.completed_at}",
        created_by=created_by,
        is_locked=True,
    )

    logger.info("Created Document %s from eDocument %s", document.pk, edocument.pk)
    return document
