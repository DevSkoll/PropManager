from django.conf import settings
from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt",
    ".txt", ".csv", ".rtf",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff",
}

ALLOWED_MIME_TYPES = {
    # PDF
    "application/pdf",
    # Microsoft Office (modern)
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    # Microsoft Office (legacy)
    "application/msword",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    # Text
    "text/plain",
    "text/csv",
    "application/rtf",
    "text/rtf",
    # Images
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/bmp",
    "image/webp",
    "image/tiff",
}

# Magic byte signatures for dangerous executable formats
DANGEROUS_SIGNATURES = [
    (b"MZ", "Windows executable"),       # PE / DOS
    (b"\x7fELF", "Linux executable"),    # ELF
    (b"#!", "Script file"),              # Shebang
]


def validate_document_file(uploaded_file):
    """Validate an uploaded file for extension, MIME type, size, and magic bytes.

    Raises ValidationError with a user-friendly message on failure.
    """
    max_size = getattr(settings, "DOCUMENT_MAX_FILE_SIZE", 25 * 1024 * 1024)

    # 1. File size check
    if uploaded_file.size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise ValidationError(
            f"File size ({uploaded_file.size / (1024 * 1024):.1f} MB) exceeds "
            f"the maximum allowed size of {max_mb:.0f} MB."
        )

    # 2. Extension whitelist
    import os
    _, ext = os.path.splitext(uploaded_file.name)
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f'File type "{ext}" is not allowed. '
            f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # 3. MIME type whitelist
    content_type = getattr(uploaded_file, "content_type", "")
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            f'File content type "{content_type}" is not allowed. '
            "Please upload a PDF, Office document, text file, or image."
        )

    # 4. Magic byte check - block dangerous executables
    uploaded_file.seek(0)
    header = uploaded_file.read(8)
    uploaded_file.seek(0)
    for signature, description in DANGEROUS_SIGNATURES:
        if header.startswith(signature):
            raise ValidationError(
                f"This file appears to be a {description}, which is not allowed. "
                "Please upload a document, spreadsheet, or image file."
            )
