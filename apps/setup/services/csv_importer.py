"""
CSV Import service for importing properties, units, and tenants during setup.
"""

import csv
import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from io import StringIO

from django.db import transaction

logger = logging.getLogger(__name__)


class CSVImporter:
    """Service for importing data from CSV files during setup."""

    # Required headers for each import type
    REQUIRED_HEADERS = {
        "properties": ["name", "property_type", "address_line1", "city", "state", "zip_code"],
        "units": ["property_name", "unit_number", "bedrooms", "base_rent"],
        "tenants": ["email", "first_name", "last_name"],
    }

    # Valid property types
    PROPERTY_TYPES = {
        "single_family": "single_family",
        "single family": "single_family",
        "singlefamily": "single_family",
        "multi_family": "multi_family",
        "multi family": "multi_family",
        "multifamily": "multi_family",
        "apartment": "apartment",
        "apartments": "apartment",
        "apartment complex": "apartment",
        "condo": "condo",
        "condominium": "condo",
        "townhouse": "townhouse",
        "commercial": "commercial",
    }

    # Valid unit statuses
    UNIT_STATUSES = {
        "vacant": "vacant",
        "available": "vacant",
        "occupied": "occupied",
        "rented": "occupied",
        "maintenance": "maintenance",
        "under maintenance": "maintenance",
    }

    def __init__(self, import_type, file_content, user=None):
        """
        Initialize the CSV importer.

        Args:
            import_type: 'properties', 'units', or 'tenants'
            file_content: CSV file content as string
            user: The user performing the import (for audit)
        """
        self.import_type = import_type
        self.file_content = file_content
        self.user = user
        self.errors = []
        self.warnings = []
        self.created_count = 0
        self.updated_count = 0

    def preview(self, limit=5):
        """
        Preview CSV data without importing.

        Args:
            limit: Maximum number of rows to preview

        Returns:
            dict with headers, rows, total_rows, and validation info
        """
        try:
            reader = csv.DictReader(StringIO(self.file_content))
            headers = reader.fieldnames or []
            rows = []

            for i, row in enumerate(reader):
                if i >= limit:
                    break
                rows.append(row)

            # Count total rows
            reader = csv.DictReader(StringIO(self.file_content))
            total_rows = sum(1 for _ in reader)

            return {
                "headers": headers,
                "rows": rows,
                "total_rows": total_rows,
                "validation": self.validate_headers(headers),
            }
        except Exception as e:
            logger.error(f"CSV preview failed: {e}")
            return {
                "headers": [],
                "rows": [],
                "total_rows": 0,
                "validation": {
                    "valid": False,
                    "missing_headers": [],
                    "error": str(e),
                },
            }

    def validate_headers(self, headers):
        """
        Validate that required headers are present.

        Args:
            headers: List of header names from CSV

        Returns:
            dict with valid boolean and missing_headers list
        """
        required = self.REQUIRED_HEADERS.get(self.import_type, [])
        # Normalize headers (lowercase, strip whitespace)
        normalized_headers = [h.lower().strip() for h in headers]
        missing = [h for h in required if h.lower() not in normalized_headers]

        return {
            "valid": len(missing) == 0,
            "missing_headers": missing,
        }

    @transaction.atomic
    def import_data(self):
        """
        Import data from CSV.

        Returns:
            dict with created, updated, errors, and warnings counts
        """
        try:
            reader = csv.DictReader(StringIO(self.file_content))

            # Normalize header names
            if reader.fieldnames:
                # Create mapping from lowercase to original
                header_map = {h.lower().strip(): h for h in reader.fieldnames}

            importers = {
                "properties": self._import_property,
                "units": self._import_unit,
                "tenants": self._import_tenant,
            }

            importer = importers.get(self.import_type)
            if not importer:
                self.errors.append(
                    {"row": 0, "error": f"Unknown import type: {self.import_type}"}
                )
                return self._get_result()

            for row_num, row in enumerate(reader, start=2):  # Header is row 1
                try:
                    # Normalize row keys
                    normalized_row = {
                        k.lower().strip(): v.strip() if isinstance(v, str) else v
                        for k, v in row.items()
                    }
                    importer(normalized_row, row_num)
                except Exception as e:
                    self.errors.append({"row": row_num, "error": str(e)})

            return self._get_result()

        except Exception as e:
            logger.error(f"CSV import failed: {e}")
            self.errors.append({"row": 0, "error": f"Import failed: {str(e)}"})
            return self._get_result()

    def _get_result(self):
        """Get the import result summary."""
        return {
            "created": self.created_count,
            "updated": self.updated_count,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    def _import_property(self, row, row_num):
        """Import a single property row."""
        from apps.properties.models import Property

        name = row.get("name", "").strip()
        if not name:
            raise ValueError("Property name is required")

        # Normalize property type
        raw_type = row.get("property_type", "apartment").lower().strip()
        property_type = self.PROPERTY_TYPES.get(raw_type)
        if not property_type:
            self.warnings.append({
                "row": row_num,
                "warning": f"Unknown property type '{raw_type}', defaulting to 'apartment'",
            })
            property_type = "apartment"

        # Parse total units
        try:
            total_units = int(row.get("total_units", 1))
        except (ValueError, TypeError):
            total_units = 1

        prop, created = Property.objects.update_or_create(
            name=name,
            defaults={
                "property_type": property_type,
                "address_line1": row.get("address_line1", ""),
                "address_line2": row.get("address_line2", ""),
                "city": row.get("city", ""),
                "state": row.get("state", ""),
                "zip_code": row.get("zip_code", ""),
                "total_units": total_units,
                "is_active": True,
                "created_by": self.user,
            },
        )

        if created:
            self.created_count += 1
        else:
            self.updated_count += 1

    def _import_unit(self, row, row_num):
        """Import a single unit row."""
        from apps.properties.models import Property, Unit

        property_name = row.get("property_name", "").strip()
        unit_number = row.get("unit_number", "").strip()

        if not property_name or not unit_number:
            raise ValueError("Property name and unit number are required")

        try:
            prop = Property.objects.get(name=property_name)
        except Property.DoesNotExist:
            raise ValueError(f"Property '{property_name}' not found")

        # Parse numeric values
        try:
            bedrooms = int(row.get("bedrooms", 1))
        except (ValueError, TypeError):
            bedrooms = 1

        try:
            bathrooms = Decimal(row.get("bathrooms", "1.0"))
        except (InvalidOperation, ValueError, TypeError):
            bathrooms = Decimal("1.0")

        try:
            square_feet_str = row.get("square_feet", "")
            square_feet = int(square_feet_str) if square_feet_str else None
        except (ValueError, TypeError):
            square_feet = None

        try:
            base_rent = Decimal(row.get("base_rent", "0"))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError("Invalid base_rent value")

        # Normalize status
        raw_status = row.get("status", "vacant").lower().strip()
        status = self.UNIT_STATUSES.get(raw_status, "vacant")

        unit, created = Unit.objects.update_or_create(
            property=prop,
            unit_number=unit_number,
            defaults={
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "square_feet": square_feet,
                "base_rent": base_rent,
                "status": status,
            },
        )

        if created:
            self.created_count += 1
        else:
            self.updated_count += 1

    def _import_tenant(self, row, row_num):
        """Import a single tenant row."""
        import secrets

        from apps.accounts.models import TenantProfile, User
        from apps.leases.models import Lease
        from apps.properties.models import Unit

        email = row.get("email", "").strip().lower()
        if not email:
            raise ValueError("Email is required")

        first_name = row.get("first_name", "").strip()
        last_name = row.get("last_name", "").strip()

        if not first_name or not last_name:
            raise ValueError("First name and last name are required")

        # Create or update user
        username = email.split("@")[0]
        # Ensure unique username
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exclude(email=email).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user, created = User.objects.update_or_create(
            email=email,
            defaults={
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "phone_number": row.get("phone_number", ""),
                "role": "tenant",
            },
        )

        if created:
            # Set a random password (tenant will use OTP login)
            user.set_password(secrets.token_urlsafe(32))
            user.save()

            # Create tenant profile
            TenantProfile.objects.get_or_create(user=user)
            self.created_count += 1
        else:
            self.updated_count += 1

        # Create lease if unit info provided
        unit_number = row.get("unit_number", "").strip()
        property_name = row.get("property_name", "").strip()

        if unit_number and property_name:
            try:
                unit = Unit.objects.get(
                    property__name=property_name, unit_number=unit_number
                )

                # Check for existing active lease on this unit
                existing_lease = Lease.objects.filter(
                    unit=unit, status__in=["active", "draft"]
                ).first()

                if existing_lease:
                    if existing_lease.tenant != user:
                        self.warnings.append({
                            "row": row_num,
                            "warning": f"Unit {unit_number} already has an active lease. Tenant created without lease.",
                        })
                    return  # Skip lease creation

                # Parse lease details
                try:
                    start_date_str = row.get("lease_start", "")
                    if start_date_str:
                        start_date = date.fromisoformat(start_date_str)
                    else:
                        start_date = date.today()
                except ValueError:
                    start_date = date.today()
                    self.warnings.append({
                        "row": row_num,
                        "warning": f"Invalid lease_start date format, using today's date.",
                    })

                try:
                    monthly_rent = Decimal(row.get("monthly_rent", str(unit.base_rent)))
                except (InvalidOperation, ValueError, TypeError):
                    monthly_rent = unit.base_rent

                # Calculate end date (default 12 months)
                from dateutil.relativedelta import relativedelta
                end_date = start_date + relativedelta(months=12)

                Lease.objects.create(
                    unit=unit,
                    tenant=user,
                    status="active",
                    lease_type="fixed",
                    start_date=start_date,
                    end_date=end_date,
                    monthly_rent=monthly_rent,
                    security_deposit=monthly_rent,  # Default to one month
                    signature_status="executed",
                    created_by=self.user,
                )

                # Update unit status to occupied
                unit.status = "occupied"
                unit.save(update_fields=["status"])

            except Unit.DoesNotExist:
                self.warnings.append({
                    "row": row_num,
                    "warning": f"Unit {unit_number} at {property_name} not found. Tenant created without lease.",
                })


def get_sample_csv_content(import_type):
    """
    Get sample CSV content for download.

    Args:
        import_type: 'properties', 'units', or 'tenants'

    Returns:
        CSV content as string
    """
    samples = {
        "properties": (
            "name,property_type,address_line1,address_line2,city,state,zip_code,total_units\n"
            "Sunset Apartments,apartment,100 Sunset Blvd,,Los Angeles,CA,90028,10\n"
            "Oak Grove Townhomes,townhouse,200 Oak St,Building A,Portland,OR,97201,8\n"
        ),
        "units": (
            "property_name,unit_number,bedrooms,bathrooms,square_feet,base_rent,status\n"
            "Sunset Apartments,101,2,1.5,850,1500.00,vacant\n"
            "Sunset Apartments,102,1,1,650,1200.00,occupied\n"
            "Oak Grove Townhomes,A1,3,2.5,1400,2200.00,vacant\n"
        ),
        "tenants": (
            "email,first_name,last_name,phone_number,unit_number,property_name,lease_start,monthly_rent\n"
            "john.doe@example.com,John,Doe,+15551234567,101,Sunset Apartments,2024-01-01,1500.00\n"
            "jane.smith@example.com,Jane,Smith,+15559876543,A1,Oak Grove Townhomes,2024-02-15,2200.00\n"
        ),
    }
    return samples.get(import_type, "")
