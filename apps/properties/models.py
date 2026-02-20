import uuid

from django.db import models

from apps.core.models import AuditMixin, TimeStampedModel


class Property(TimeStampedModel, AuditMixin):
    PROPERTY_TYPE_CHOICES = [
        ("single_family", "Single Family"),
        ("multi_family", "Multi Family"),
        ("apartment", "Apartment Complex"),
        ("condo", "Condominium"),
        ("townhouse", "Townhouse"),
        ("commercial", "Commercial"),
    ]

    name = models.CharField(max_length=200)
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPE_CHOICES)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=10)
    total_units = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True, db_index=True)
    description = models.TextField(blank=True, default="")

    # Property manager contact info (for tenant display)
    manager_name = models.CharField(max_length=100, blank=True, default="")
    manager_email = models.EmailField(blank=True, default="")
    manager_phone = models.CharField(max_length=20, blank=True, default="")
    office_address = models.CharField(max_length=255, blank=True, default="")
    office_hours = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        verbose_name_plural = "Properties"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def full_address(self):
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        parts.append(f"{self.city}, {self.state} {self.zip_code}")
        return ", ".join(parts)

    @property
    def occupied_units_count(self):
        return self.units.filter(status="occupied").count()

    @property
    def vacant_units_count(self):
        return self.units.filter(status="vacant").count()


class Unit(TimeStampedModel):
    STATUS_CHOICES = [
        ("vacant", "Vacant"),
        ("occupied", "Occupied"),
        ("maintenance", "Under Maintenance"),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="units")
    unit_number = models.CharField(max_length=20)
    bedrooms = models.PositiveSmallIntegerField(default=1)
    bathrooms = models.DecimalField(max_digits=3, decimal_places=1, default=1.0)
    square_feet = models.PositiveIntegerField(null=True, blank=True)
    base_rent = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="vacant", db_index=True)
    floor = models.PositiveSmallIntegerField(null=True, blank=True)
    description = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["property", "unit_number"]
        unique_together = [("property", "unit_number")]

    def __str__(self):
        return f"{self.property.name} - Unit {self.unit_number}"


class Amenity(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        verbose_name_plural = "Amenities"
        ordering = ["name"]

    def __str__(self):
        return self.name


class UnitAmenity(TimeStampedModel):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="unit_amenities")
    amenity = models.ForeignKey(Amenity, on_delete=models.CASCADE, related_name="unit_amenities")
    notes = models.TextField(blank=True, default="")

    class Meta:
        unique_together = [("unit", "amenity")]
        verbose_name_plural = "Unit Amenities"

    def __str__(self):
        return f"{self.unit} - {self.amenity}"
