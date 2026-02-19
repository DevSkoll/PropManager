from datetime import timedelta

from django.utils import timezone


def purge_deleted_documents():
    """Permanently delete documents that were soft-deleted more than 7 days ago.

    Removes both the file from storage and the database row.
    Intended to be scheduled as a daily task via Django-Q2.
    """
    from .models import Document

    cutoff = timezone.now() - timedelta(days=7)
    expired = Document.all_objects.filter(deleted_at__lte=cutoff)
    count = 0
    for doc in expired.iterator():
        doc.file.delete(save=False)
        doc.delete()
        count += 1
    return f"Purged {count} expired document(s)."
