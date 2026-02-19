from django.contrib import admin

from .models import (
    BillingCycle,
    Invoice,
    InvoiceLineItem,
    Payment,
    PaymentGatewayConfig,
    PrepaymentCredit,
)


@admin.register(PaymentGatewayConfig)
class PaymentGatewayConfigAdmin(admin.ModelAdmin):
    list_display = ("display_name", "provider", "is_active", "is_default")
    list_filter = ("provider", "is_active", "is_default")


@admin.register(BillingCycle)
class BillingCycleAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "is_closed")
    list_filter = ("is_closed",)


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "tenant", "status", "total_amount", "amount_paid", "due_date")
    list_filter = ("status",)
    search_fields = ("invoice_number", "tenant__username", "tenant__email")
    inlines = [InvoiceLineItemInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("tenant", "invoice", "amount", "method", "status", "payment_date")
    list_filter = ("status", "method")
    search_fields = ("tenant__username", "reference_number")


@admin.register(PrepaymentCredit)
class PrepaymentCreditAdmin(admin.ModelAdmin):
    list_display = ("tenant", "amount", "remaining_amount", "reason")
