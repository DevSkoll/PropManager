from django.contrib import admin

from .models import Amenity, Property, Unit, UnitAmenity


class UnitInline(admin.TabularInline):
    model = Unit
    extra = 0


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("name", "property_type", "city", "state", "total_units", "is_active")
    list_filter = ("property_type", "state", "is_active")
    search_fields = ("name", "address_line1", "city")
    inlines = [UnitInline]


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("__str__", "bedrooms", "bathrooms", "base_rent", "status")
    list_filter = ("status", "property")
    search_fields = ("unit_number", "property__name")


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ("name", "icon")
    search_fields = ("name",)


@admin.register(UnitAmenity)
class UnitAmenityAdmin(admin.ModelAdmin):
    list_display = ("unit", "amenity")
    list_filter = ("amenity",)
