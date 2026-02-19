from django.contrib import admin

from .models import (
    ApiToken,
    BillingCycle,
    Invoice,
    InvoiceLineItem,
    LateFeeLog,
    Payment,
    PaymentGatewayConfig,
    PrepaymentCredit,
    PropertyBillingConfig,
    RecurringCharge,
    UtilityConfig,
    UtilityRateLog,
)


@admin.register(PaymentGatewayConfig)
class PaymentGatewayConfigAdmin(admin.ModelAdmin):
    list_display = ("display_name", "provider", "is_active", "is_default")
    list_filter = ("provider", "is_active", "is_default")


@admin.register(BillingCycle)
class BillingCycleAdmin(admin.ModelAdmin):
    list_display = ("name", "property", "start_date", "end_date", "is_closed")
    list_filter = ("is_closed",)


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "tenant", "status", "total_amount", "amount_paid", "late_fees_total", "due_date")
    list_filter = ("status",)
    search_fields = ("invoice_number", "tenant__username", "tenant__email")
    inlines = [InvoiceLineItemInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("tenant", "invoice", "amount", "method", "status", "credit_applied", "payment_date")
    list_filter = ("status", "method")
    search_fields = ("tenant__username", "reference_number")


@admin.register(PrepaymentCredit)
class PrepaymentCreditAdmin(admin.ModelAdmin):
    list_display = ("tenant", "amount", "remaining_amount", "reason")


@admin.register(UtilityConfig)
class UtilityConfigAdmin(admin.ModelAdmin):
    list_display = ("unit", "utility_type", "billing_mode", "rate", "is_active")
    list_filter = ("utility_type", "billing_mode", "is_active")
    search_fields = ("unit__unit_number", "unit__property__name")


@admin.register(UtilityRateLog)
class UtilityRateLogAdmin(admin.ModelAdmin):
    list_display = ("utility_config", "previous_rate", "new_rate", "previous_billing_mode", "new_billing_mode", "source", "created_at")
    list_filter = ("source", "new_billing_mode")
    search_fields = ("utility_config__unit__unit_number",)
    readonly_fields = ("utility_config", "previous_rate", "new_rate", "previous_billing_mode", "new_billing_mode", "changed_by", "source", "notes")


@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    list_display = ("label", "user", "is_active", "last_used_at", "created_at")
    list_filter = ("is_active",)
    search_fields = ("label", "user__username")


@admin.register(PropertyBillingConfig)
class PropertyBillingConfigAdmin(admin.ModelAdmin):
    list_display = ("property", "auto_generate_invoices", "late_fee_enabled", "grace_period_days", "late_fee_type", "late_fee_amount")
    list_filter = ("auto_generate_invoices", "late_fee_enabled")


@admin.register(RecurringCharge)
class RecurringChargeAdmin(admin.ModelAdmin):
    list_display = ("description", "charge_type", "amount", "frequency", "lease", "property", "is_active")
    list_filter = ("charge_type", "frequency", "is_active")
    search_fields = ("description",)


@admin.register(LateFeeLog)
class LateFeeLogAdmin(admin.ModelAdmin):
    list_display = ("invoice", "fee_type", "amount", "applied_date")
    list_filter = ("fee_type",)
    readonly_fields = ("invoice", "line_item", "fee_type", "amount", "applied_date", "notes")
