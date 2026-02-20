"""
Markdown parser for eDocument signature tags.

Parses [SIGNATURE:Role] and [INITIALS:Role] tags from markdown content
and extracts the required signers and signature blocks.
"""

import re
from dataclasses import dataclass
from typing import Literal


# Regex patterns for signature tags
SIGNATURE_TAG_PATTERN = re.compile(
    r'\[(?P<type>SIGNATURE|INITIALS):(?P<role>[A-Za-z0-9_]+)\]',
    re.IGNORECASE
)

# Valid signer roles (normalized to lowercase)
VALID_ROLES = {
    "landlord",
    "tenant",
    "tenant2",
    "tenant3",
    "tenant4",
    "cosigner",
}


@dataclass
class SignatureTag:
    """Represents a parsed signature tag from the document."""
    tag_type: Literal["signature", "initials"]
    role: str
    position: int  # Character position in the document
    order: int  # Order of appearance (1-indexed)
    original_text: str  # The original tag text


@dataclass
class ParsedDocument:
    """Result of parsing an eDocument markdown content."""
    tags: list[SignatureTag]
    roles: set[str]
    errors: list[str]

    @property
    def signature_count(self) -> int:
        """Total number of signature tags."""
        return len(self.tags)

    @property
    def unique_roles(self) -> list[str]:
        """List of unique roles in appearance order."""
        seen = []
        for tag in self.tags:
            if tag.role not in seen:
                seen.append(tag.role)
        return seen


def parse_signature_tags(content: str) -> ParsedDocument:
    """
    Parse signature and initials tags from markdown content.

    Args:
        content: Markdown content with [SIGNATURE:Role] and [INITIALS:Role] tags

    Returns:
        ParsedDocument with extracted tags, roles, and any errors
    """
    tags = []
    roles = set()
    errors = []
    order = 0

    for match in SIGNATURE_TAG_PATTERN.finditer(content):
        order += 1
        tag_type = match.group("type").lower()
        role = match.group("role").lower()
        original = match.group(0)
        position = match.start()

        # Validate role
        if role not in VALID_ROLES:
            errors.append(
                f"Unknown role '{role}' in tag '{original}' at position {position}. "
                f"Valid roles: {', '.join(sorted(VALID_ROLES))}"
            )
            continue

        tags.append(SignatureTag(
            tag_type=tag_type,
            role=role,
            position=position,
            order=order,
            original_text=original,
        ))
        roles.add(role)

    return ParsedDocument(tags=tags, roles=roles, errors=errors)


def extract_required_roles(content: str) -> list[str]:
    """
    Extract list of unique roles required to sign the document.

    Args:
        content: Markdown content

    Returns:
        List of role names in order of first appearance
    """
    parsed = parse_signature_tags(content)
    return parsed.unique_roles


def get_blocks_for_role(content: str, role: str) -> list[SignatureTag]:
    """
    Get all signature/initials blocks for a specific role.

    Args:
        content: Markdown content
        role: Role name (e.g., "tenant", "landlord")

    Returns:
        List of SignatureTag for the specified role
    """
    parsed = parse_signature_tags(content)
    return [tag for tag in parsed.tags if tag.role == role.lower()]


def validate_document(content: str) -> tuple[bool, list[str]]:
    """
    Validate document content for signature tags.

    Args:
        content: Markdown content

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    parsed = parse_signature_tags(content)
    errors = list(parsed.errors)

    if not parsed.tags:
        errors.append("Document must contain at least one [SIGNATURE:Role] or [INITIALS:Role] tag.")

    return (len(errors) == 0, errors)


def render_signature_placeholder(tag: SignatureTag, signed: bool = False, image: str = "") -> str:
    """
    Render a signature tag as HTML placeholder or signed image.

    Args:
        tag: The signature tag to render
        signed: Whether the signature has been captured
        image: Base64 image data if signed

    Returns:
        HTML string for the signature block
    """
    block_class = "signature-block" if tag.tag_type == "signature" else "initials-block"
    role_display = tag.role.replace("_", " ").title()

    if signed and image:
        return f'''
<div class="{block_class} signed" data-role="{tag.role}" data-order="{tag.order}">
    <img src="{image}" alt="{role_display} {tag.tag_type}" class="signature-image">
    <span class="signature-label">{role_display}</span>
</div>
'''
    else:
        size_class = "signature-canvas" if tag.tag_type == "signature" else "initials-canvas"
        return f'''
<div class="{block_class} pending" data-role="{tag.role}" data-order="{tag.order}" data-type="{tag.tag_type}">
    <div class="signature-placeholder {size_class}">
        <span class="placeholder-text">Sign here: {role_display}</span>
    </div>
    <span class="signature-label">{role_display}</span>
</div>
'''


def replace_tags_with_html(
    content: str,
    signed_blocks: dict[int, str] | None = None,
    current_role: str | None = None,
) -> str:
    """
    Replace signature tags with HTML blocks.

    Args:
        content: Markdown content with signature tags
        signed_blocks: Dict mapping block order to base64 image (for signed blocks)
        current_role: If provided, only show interactive placeholders for this role

    Returns:
        Content with tags replaced by HTML
    """
    signed_blocks = signed_blocks or {}

    def replacer(match):
        tag_type = match.group("type").lower()
        role = match.group("role").lower()

        # Find the order for this specific match
        all_matches = list(SIGNATURE_TAG_PATTERN.finditer(content))
        order = next(
            (i + 1 for i, m in enumerate(all_matches) if m.start() == match.start()),
            0
        )

        tag = SignatureTag(
            tag_type=tag_type,
            role=role,
            position=match.start(),
            order=order,
            original_text=match.group(0),
        )

        is_signed = order in signed_blocks
        image = signed_blocks.get(order, "")

        return render_signature_placeholder(tag, signed=is_signed, image=image)

    return SIGNATURE_TAG_PATTERN.sub(replacer, content)


def count_blocks_by_role(content: str) -> dict[str, dict[str, int]]:
    """
    Count signature and initials blocks per role.

    Args:
        content: Markdown content

    Returns:
        Dict mapping role to {"signature": count, "initials": count}
    """
    parsed = parse_signature_tags(content)
    counts = {}

    for tag in parsed.tags:
        if tag.role not in counts:
            counts[tag.role] = {"signature": 0, "initials": 0}
        counts[tag.role][tag.tag_type] += 1

    return counts
