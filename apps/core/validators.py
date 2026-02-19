import re

from django.core.exceptions import ValidationError


def validate_phone_number(value):
    pattern = re.compile(r"^\+?1?\d{10,15}$")
    if not pattern.match(value):
        raise ValidationError("Enter a valid phone number (10-15 digits, optional + prefix).")
