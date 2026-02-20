"""
Template Variable Resolver for eDocuments.

Resolves {{variable}} placeholders in markdown templates with actual data
from lease, property, unit, tenant, and other context objects.
"""

import re
from decimal import Decimal
from typing import Any

from django.utils import timezone


# Variable placeholder pattern
VARIABLE_PATTERN = re.compile(r'\{\{(\w+)\}\}')


class TemplateVariableResolver:
    """
    Resolves template variables from context objects.

    Usage:
        resolver = TemplateVariableResolver(lease=lease)
        content = resolver.substitute(template_content)
        # or
        variables = resolver.resolve_all()
    """

    # Variable definitions with categories for documentation
    VARIABLE_DEFINITIONS = {
        # Lease Variables
        "lease_start_date": ("lease", "Start date of the lease"),
        "lease_end_date": ("lease", "End date of the lease"),
        "lease_type": ("lease", "Type of lease (Fixed Term/Month-to-Month)"),
        "monthly_rent": ("lease", "Monthly rent amount"),
        "monthly_rent_numeric": ("lease", "Monthly rent as number (no formatting)"),
        "security_deposit": ("lease", "Security deposit amount"),
        "rent_due_day": ("lease", "Day of month rent is due"),
        "grace_period_days": ("lease", "Grace period before late fees"),
        "late_fee_amount": ("lease", "Late fee amount"),
        "max_occupants": ("lease", "Maximum allowed occupants"),
        "pets_allowed": ("lease", "Whether pets are allowed (Yes/No)"),
        "max_pets": ("lease", "Maximum number of pets"),
        "smoking_allowed": ("lease", "Whether smoking is allowed (Yes/No)"),
        "parking_spaces": ("lease", "Number of parking spaces"),
        "parking_space_numbers": ("lease", "Assigned parking space numbers"),
        "utilities_included": ("lease", "List of included utilities"),

        # Property Variables
        "property_name": ("property", "Property name"),
        "property_address": ("property", "Full property address"),
        "property_address_line1": ("property", "Street address"),
        "property_city": ("property", "City"),
        "property_state": ("property", "State"),
        "property_zip": ("property", "ZIP code"),
        "manager_name": ("property", "Property manager name"),
        "manager_email": ("property", "Property manager email"),
        "manager_phone": ("property", "Property manager phone"),
        "office_address": ("property", "Office address"),
        "office_hours": ("property", "Office hours"),

        # Unit Variables
        "unit_number": ("unit", "Unit number/identifier"),
        "unit_bedrooms": ("unit", "Number of bedrooms"),
        "unit_bathrooms": ("unit", "Number of bathrooms"),
        "unit_square_feet": ("unit", "Square footage"),
        "unit_floor": ("unit", "Floor number"),

        # Tenant Variables
        "tenant_name": ("tenant", "Primary tenant full name"),
        "tenant_first_name": ("tenant", "Tenant first name"),
        "tenant_last_name": ("tenant", "Tenant last name"),
        "tenant_email": ("tenant", "Tenant email address"),
        "tenant_phone": ("tenant", "Tenant phone number"),

        # Occupant Variables
        "all_occupant_names": ("occupants", "All occupant names (comma-separated)"),
        "occupant_count": ("occupants", "Total number of occupants"),

        # Date Variables
        "current_date": ("dates", "Today's date"),
        "current_year": ("dates", "Current year"),

        # Landlord Variables
        "landlord_name": ("landlord", "Landlord/manager name"),
    }

    def __init__(
        self,
        lease=None,
        property_obj=None,
        unit=None,
        tenant=None,
        landlord_user=None,
        extra_variables: dict | None = None,
    ):
        """
        Initialize resolver with context objects.

        Args:
            lease: Lease model instance
            property_obj: Property model instance
            unit: Unit model instance
            tenant: User model instance (tenant)
            landlord_user: User model instance (landlord/admin)
            extra_variables: Additional custom variables
        """
        self.lease = lease
        self.property_obj = property_obj or self._get_property_from_context(lease, unit)
        self.unit = unit or (lease.unit if lease else None)
        self.tenant = tenant or (lease.tenant if lease else None)
        self.landlord_user = landlord_user
        self.extra_variables = extra_variables or {}

    def _get_property_from_context(self, lease, unit):
        """Extract property from available context."""
        if unit and hasattr(unit, "property"):
            return unit.property
        if lease and hasattr(lease, "unit") and lease.unit:
            return lease.unit.property
        return None

    def resolve_all(self) -> dict[str, str]:
        """Return dict of all resolved variables."""
        variables = {}

        # Lease variables
        if self.lease:
            variables.update(self._resolve_lease_variables())

        # Property variables
        if self.property_obj:
            variables.update(self._resolve_property_variables())

        # Unit variables
        if self.unit:
            variables.update(self._resolve_unit_variables())

        # Tenant variables
        if self.tenant:
            variables.update(self._resolve_tenant_variables())

        # Occupant variables (from lease)
        if self.lease:
            variables.update(self._resolve_occupant_variables())

        # Landlord variables
        if self.landlord_user:
            variables.update(self._resolve_landlord_variables())

        # Date variables
        variables.update(self._resolve_date_variables())

        # Extra custom variables
        variables.update(self.extra_variables)

        return variables

    def _resolve_lease_variables(self) -> dict[str, str]:
        """Resolve lease-related variables."""
        lease = self.lease
        return {
            "lease_start_date": self._format_date(lease.start_date) if lease.start_date else "",
            "lease_end_date": self._format_date(lease.end_date) if lease.end_date else "Month-to-Month",
            "lease_type": lease.get_lease_type_display() if hasattr(lease, "get_lease_type_display") else str(lease.lease_type),
            "monthly_rent": self._format_currency(lease.monthly_rent),
            "monthly_rent_numeric": str(lease.monthly_rent) if lease.monthly_rent else "0",
            "security_deposit": self._format_currency(lease.security_deposit),
            "rent_due_day": self._ordinal(lease.rent_due_day) if lease.rent_due_day else "1st",
            "grace_period_days": str(lease.grace_period_days) if hasattr(lease, "grace_period_days") else "5",
            "late_fee_amount": self._format_currency(lease.late_fee_amount) if hasattr(lease, "late_fee_amount") else "$0.00",
            "max_occupants": str(getattr(lease, "max_occupants", "")),
            "pets_allowed": "Yes" if getattr(lease, "pets_allowed", False) else "No",
            "max_pets": str(getattr(lease, "max_pets", 0)),
            "smoking_allowed": "Yes" if getattr(lease, "smoking_allowed", False) else "No",
            "parking_spaces": str(getattr(lease, "parking_spaces", 0)),
            "parking_space_numbers": getattr(lease, "parking_space_numbers", "") or "N/A",
            "utilities_included": ", ".join(getattr(lease, "utilities_included", [])) if getattr(lease, "utilities_included", None) else "None",
        }

    def _resolve_property_variables(self) -> dict[str, str]:
        """Resolve property-related variables."""
        prop = self.property_obj
        full_address = self._build_full_address(prop)

        return {
            "property_name": prop.name,
            "property_address": full_address,
            "property_address_line1": getattr(prop, "address_line1", "") or getattr(prop, "address", ""),
            "property_city": getattr(prop, "city", ""),
            "property_state": getattr(prop, "state", ""),
            "property_zip": getattr(prop, "zip_code", "") or getattr(prop, "postal_code", ""),
            "manager_name": getattr(prop, "manager_name", "") or "Property Manager",
            "manager_email": getattr(prop, "manager_email", "") or "",
            "manager_phone": getattr(prop, "manager_phone", "") or "",
            "office_address": getattr(prop, "office_address", "") or "",
            "office_hours": getattr(prop, "office_hours", "") or "",
        }

    def _resolve_unit_variables(self) -> dict[str, str]:
        """Resolve unit-related variables."""
        unit = self.unit
        return {
            "unit_number": getattr(unit, "unit_number", "") or str(unit),
            "unit_bedrooms": str(getattr(unit, "bedrooms", "")),
            "unit_bathrooms": str(getattr(unit, "bathrooms", "")),
            "unit_square_feet": str(getattr(unit, "square_feet", "")) if getattr(unit, "square_feet", None) else "N/A",
            "unit_floor": str(getattr(unit, "floor", "")) if getattr(unit, "floor", None) else "N/A",
        }

    def _resolve_tenant_variables(self) -> dict[str, str]:
        """Resolve tenant-related variables."""
        tenant = self.tenant
        full_name = tenant.get_full_name() if hasattr(tenant, "get_full_name") else f"{tenant.first_name} {tenant.last_name}".strip()

        return {
            "tenant_name": full_name or getattr(tenant, "username", ""),
            "tenant_first_name": getattr(tenant, "first_name", "") or "",
            "tenant_last_name": getattr(tenant, "last_name", "") or "",
            "tenant_email": getattr(tenant, "email", "") or "",
            "tenant_phone": getattr(tenant, "phone_number", "") or getattr(tenant, "phone", "") or "",
        }

    def _resolve_occupant_variables(self) -> dict[str, str]:
        """Resolve occupant-related variables."""
        occupants = []
        if hasattr(self.lease, "occupants"):
            try:
                occupant_qs = self.lease.occupants.all()
                occupants = [f"{o.first_name} {o.last_name}".strip() for o in occupant_qs]
            except Exception:
                pass

        # Include primary tenant in count
        count = len(occupants) + 1 if self.tenant else len(occupants)

        return {
            "all_occupant_names": ", ".join(occupants) if occupants else "None",
            "occupant_count": str(count),
        }

    def _resolve_landlord_variables(self) -> dict[str, str]:
        """Resolve landlord-related variables."""
        landlord = self.landlord_user
        full_name = ""
        if landlord:
            full_name = landlord.get_full_name() if hasattr(landlord, "get_full_name") else f"{landlord.first_name} {landlord.last_name}".strip()
            full_name = full_name or getattr(landlord, "username", "Landlord")

        return {
            "landlord_name": full_name or "Landlord",
        }

    def _resolve_date_variables(self) -> dict[str, str]:
        """Resolve date-related variables."""
        now = timezone.now()
        return {
            "current_date": now.strftime("%B %d, %Y"),
            "current_year": str(now.year),
        }

    def resolve(self, variable_name: str) -> str:
        """Resolve a single variable."""
        all_vars = self.resolve_all()
        return all_vars.get(variable_name, f"{{{{UNKNOWN:{variable_name}}}}}")

    def substitute(self, content: str) -> str:
        """
        Replace all {{variable}} placeholders in content.

        Args:
            content: Template content with {{variable}} placeholders

        Returns:
            Content with variables substituted
        """
        variables = self.resolve_all()

        def replacer(match):
            var_name = match.group(1).strip()
            return variables.get(var_name, match.group(0))

        return VARIABLE_PATTERN.sub(replacer, content)

    def get_unresolved_variables(self, content: str) -> list[str]:
        """
        Find variables in content that couldn't be resolved.

        Args:
            content: Template content

        Returns:
            List of unresolved variable names
        """
        variables = self.resolve_all()
        unresolved = []

        for match in VARIABLE_PATTERN.finditer(content):
            var_name = match.group(1).strip()
            if var_name not in variables:
                unresolved.append(var_name)

        return list(set(unresolved))

    # Helper methods
    @staticmethod
    def _format_currency(value: Any) -> str:
        """Format a value as currency."""
        if value is None:
            return "$0.00"
        try:
            amount = Decimal(str(value))
            return f"${amount:,.2f}"
        except (ValueError, TypeError):
            return "$0.00"

    @staticmethod
    def _format_date(value) -> str:
        """Format a date value."""
        if value is None:
            return ""
        try:
            return value.strftime("%B %d, %Y")
        except AttributeError:
            return str(value)

    @staticmethod
    def _ordinal(n: int) -> str:
        """Convert number to ordinal (1st, 2nd, 3rd, etc.)."""
        try:
            n = int(n)
        except (ValueError, TypeError):
            return str(n)

        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
        if 11 <= (n % 100) <= 13:
            suffix = 'th'
        return f"{n}{suffix}"

    @staticmethod
    def _build_full_address(prop) -> str:
        """Build full address string from property."""
        parts = []
        if getattr(prop, "address_line1", None):
            parts.append(prop.address_line1)
        elif getattr(prop, "address", None):
            parts.append(prop.address)

        city_state_zip = []
        if getattr(prop, "city", None):
            city_state_zip.append(prop.city)
        if getattr(prop, "state", None):
            city_state_zip.append(prop.state)
        if city_state_zip:
            parts.append(", ".join(city_state_zip))

        zip_code = getattr(prop, "zip_code", None) or getattr(prop, "postal_code", None)
        if zip_code:
            parts.append(zip_code)

        return " ".join(parts) if parts else ""


def get_available_variables() -> dict[str, list[tuple[str, str]]]:
    """
    Get available variables grouped by category.

    Returns:
        Dict mapping category to list of (variable_name, description) tuples
    """
    grouped = {}
    for var_name, (category, description) in TemplateVariableResolver.VARIABLE_DEFINITIONS.items():
        if category not in grouped:
            grouped[category] = []
        grouped[category].append((var_name, description))

    # Sort each category's variables
    for category in grouped:
        grouped[category].sort(key=lambda x: x[0])

    return grouped


def get_sample_variables() -> dict[str, str]:
    """
    Get sample variable values for preview.

    Returns:
        Dict of variable names to sample values
    """
    return {
        # Lease
        "lease_start_date": "January 1, 2024",
        "lease_end_date": "December 31, 2024",
        "lease_type": "Fixed Term",
        "monthly_rent": "$1,500.00",
        "monthly_rent_numeric": "1500.00",
        "security_deposit": "$1,500.00",
        "rent_due_day": "1st",
        "grace_period_days": "5",
        "late_fee_amount": "$100.00",
        "max_occupants": "4",
        "pets_allowed": "No",
        "max_pets": "0",
        "smoking_allowed": "No",
        "parking_spaces": "1",
        "parking_space_numbers": "A-12",
        "utilities_included": "Water, Trash",

        # Property
        "property_name": "Sample Property",
        "property_address": "123 Main Street, Anchorage, AK 99501",
        "property_address_line1": "123 Main Street",
        "property_city": "Anchorage",
        "property_state": "AK",
        "property_zip": "99501",
        "manager_name": "Property Manager",
        "manager_email": "manager@example.com",
        "manager_phone": "(907) 555-1234",
        "office_address": "456 Office Ave, Suite 200",
        "office_hours": "Mon-Fri 9am-5pm",

        # Unit
        "unit_number": "101",
        "unit_bedrooms": "2",
        "unit_bathrooms": "1",
        "unit_square_feet": "850",
        "unit_floor": "1",

        # Tenant
        "tenant_name": "John Smith",
        "tenant_first_name": "John",
        "tenant_last_name": "Smith",
        "tenant_email": "john.smith@example.com",
        "tenant_phone": "(907) 555-5678",

        # Occupants
        "all_occupant_names": "Jane Smith, Junior Smith",
        "occupant_count": "3",

        # Dates
        "current_date": timezone.now().strftime("%B %d, %Y"),
        "current_year": str(timezone.now().year),

        # Landlord
        "landlord_name": "Landlord Name",
    }
