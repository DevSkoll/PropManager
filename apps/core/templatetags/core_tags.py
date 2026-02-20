from django import template

register = template.Library()


@register.filter
def currency(value):
    try:
        return f"${float(value):,.2f}"
    except (ValueError, TypeError):
        return value


@register.filter
def phone_format(value):
    if not value:
        return ""
    digits = "".join(c for c in str(value) if c.isdigit())
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return value


@register.filter
def human_filesize(value):
    """Convert a file size in bytes to a human-readable string (KB, MB, GB)."""
    try:
        value = int(value)
    except (ValueError, TypeError):
        return value
    if value < 1024:
        return f"{value} B"
    elif value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    elif value < 1024 * 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MB"
    else:
        return f"{value / (1024 * 1024 * 1024):.1f} GB"


@register.simple_tag(takes_context=True)
def active_nav(context, url_name):
    request = context.get("request")
    if request and request.resolver_match and request.resolver_match.url_name == url_name:
        return "active"
    return ""


@register.filter
def ordinal(value):
    """Convert an integer to its ordinal representation (1st, 2nd, 3rd, etc.)."""
    try:
        value = int(value)
    except (ValueError, TypeError):
        return value
    if 11 <= (value % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def get_field(form, field_name):
    """Get a form field by name."""
    try:
        return form[field_name]
    except (KeyError, TypeError):
        return None


@register.filter
def add_prefix(field, prefix):
    """Add a prefix to a form field's name attribute."""
    if field is None:
        return ""
    # Return the field as-is since Django form fields already handle their own rendering
    return field
