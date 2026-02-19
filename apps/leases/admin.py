from django.contrib import admin

from .models import Lease, LeaseTerm, LeaseTermination


class LeaseTermInline(admin.TabularInline):
    model = LeaseTerm
    extra = 0


@admin.register(Lease)
class LeaseAdmin(admin.ModelAdmin):
    list_display = ("tenant", "unit", "status", "lease_type", "start_date", "end_date", "monthly_rent")
    list_filter = ("status", "lease_type")
    search_fields = ("tenant__username", "tenant__email", "unit__unit_number", "unit__property__name")
    inlines = [LeaseTermInline]


@admin.register(LeaseTerm)
class LeaseTermAdmin(admin.ModelAdmin):
    list_display = ("lease", "title", "is_standard")
    list_filter = ("is_standard",)


@admin.register(LeaseTermination)
class LeaseTerminationAdmin(admin.ModelAdmin):
    list_display = ("lease", "termination_date", "early_termination_fee", "fee_paid")
