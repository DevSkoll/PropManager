from django.contrib import admin

from .models import (
    Lease,
    LeaseFee,
    LeaseOccupant,
    LeasePet,
    LeaseSignature,
    LeaseTerm,
    LeaseTermination,
)


class LeaseTermInline(admin.TabularInline):
    model = LeaseTerm
    extra = 0


class LeaseOccupantInline(admin.TabularInline):
    model = LeaseOccupant
    extra = 0
    fields = [
        "first_name", "last_name", "relationship", "email", "phone",
        "is_on_lease", "is_cosigner",
    ]


class LeasePetInline(admin.TabularInline):
    model = LeasePet
    extra = 0
    fields = [
        "pet_type", "name", "breed", "weight_lbs",
        "is_service_animal", "vaccination_current",
        "pet_deposit", "monthly_pet_rent",
    ]


class LeaseFeeInline(admin.TabularInline):
    model = LeaseFee
    extra = 0
    fields = ["fee_type", "name", "amount", "frequency", "is_refundable"]


class LeaseSignatureInline(admin.TabularInline):
    model = LeaseSignature
    extra = 0
    fields = [
        "signer_type", "signer_name", "signer_email",
        "signed_at", "ip_address",
    ]
    readonly_fields = ["signed_at", "ip_address"]


@admin.register(Lease)
class LeaseAdmin(admin.ModelAdmin):
    list_display = (
        "tenant", "unit", "status", "signature_status",
        "lease_type", "start_date", "end_date", "monthly_rent",
    )
    list_filter = ("status", "signature_status", "lease_type", "pets_allowed")
    search_fields = (
        "tenant__username", "tenant__email",
        "unit__unit_number", "unit__property__name",
    )
    readonly_fields = (
        "signature_requested_at", "fully_executed_at",
        "created_at", "updated_at",
    )
    inlines = [
        LeaseTermInline,
        LeaseOccupantInline,
        LeasePetInline,
        LeaseFeeInline,
        LeaseSignatureInline,
    ]

    fieldsets = (
        ("Core Information", {
            "fields": (
                "unit", "tenant", "status", "lease_type",
                "start_date", "end_date", "previous_lease",
            )
        }),
        ("Rent & Deposits", {
            "fields": (
                "monthly_rent", "security_deposit",
                "rent_due_day", "grace_period_days",
                "late_fee_amount", "late_fee_type",
            )
        }),
        ("Occupancy & Pets", {
            "fields": (
                "max_occupants", "pets_allowed", "max_pets",
            )
        }),
        ("Policies", {
            "fields": (
                "smoking_allowed", "subletting_allowed",
                "renters_insurance_required", "renters_insurance_minimum",
                "utilities_included",
            )
        }),
        ("Renewal Terms", {
            "fields": (
                "auto_renewal", "renewal_notice_days", "rent_increase_notice_days",
            ),
            "classes": ("collapse",),
        }),
        ("Parking", {
            "fields": ("parking_spaces", "parking_space_numbers"),
            "classes": ("collapse",),
        }),
        ("Move-In/Out", {
            "fields": (
                "move_in_date", "move_out_date",
                "move_in_inspection_complete", "move_out_inspection_complete",
            ),
            "classes": ("collapse",),
        }),
        ("Signature Workflow", {
            "fields": (
                "signature_status", "signature_requested_at", "fully_executed_at",
            ),
        }),
        ("Notes & Metadata", {
            "fields": ("notes", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(LeaseTerm)
class LeaseTermAdmin(admin.ModelAdmin):
    list_display = ("lease", "title", "is_standard")
    list_filter = ("is_standard",)
    search_fields = ("title", "description", "lease__tenant__username")


@admin.register(LeaseTermination)
class LeaseTerminationAdmin(admin.ModelAdmin):
    list_display = ("lease", "termination_date", "early_termination_fee", "fee_paid")
    list_filter = ("fee_paid",)


@admin.register(LeaseOccupant)
class LeaseOccupantAdmin(admin.ModelAdmin):
    list_display = (
        "full_name", "lease", "relationship", "is_on_lease", "is_cosigner",
    )
    list_filter = ("relationship", "is_on_lease", "is_cosigner")
    search_fields = ("first_name", "last_name", "email")


@admin.register(LeasePet)
class LeasePetAdmin(admin.ModelAdmin):
    list_display = (
        "name", "pet_type", "lease", "breed",
        "is_service_animal", "vaccination_current",
    )
    list_filter = ("pet_type", "is_service_animal", "vaccination_current")
    search_fields = ("name", "breed")


@admin.register(LeaseFee)
class LeaseFeeAdmin(admin.ModelAdmin):
    list_display = ("name", "fee_type", "lease", "amount", "frequency", "is_refundable")
    list_filter = ("fee_type", "frequency", "is_refundable")
    search_fields = ("name", "description")


@admin.register(LeaseSignature)
class LeaseSignatureAdmin(admin.ModelAdmin):
    list_display = (
        "signer_name", "signer_type", "lease", "signed_at", "ip_address",
    )
    list_filter = ("signer_type",)
    search_fields = ("signer_name", "signer_email")
    readonly_fields = (
        "signing_token", "signed_at", "ip_address", "user_agent",
        "signature_image",
    )
