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


@register.simple_tag(takes_context=True)
def active_nav(context, url_name):
    request = context.get("request")
    if request and request.resolver_match and request.resolver_match.url_name == url_name:
        return "active"
    return ""
