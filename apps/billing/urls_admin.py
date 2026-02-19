from django.urls import path

from . import views

app_name = "billing_admin"

urlpatterns = [
    path("billing/invoices/", views.admin_invoice_list, name="invoice_list"),
    path("billing/invoices/create/", views.admin_invoice_create, name="invoice_create"),
    path("billing/invoices/generate/", views.admin_invoice_generate_batch, name="invoice_generate_batch"),
    path("billing/invoices/<uuid:pk>/", views.admin_invoice_detail, name="invoice_detail"),
    path("billing/invoices/<uuid:pk>/edit/", views.admin_invoice_edit, name="invoice_edit"),
    path("billing/invoices/<uuid:pk>/apply-late-fee/", views.admin_invoice_apply_late_fee, name="invoice_apply_late_fee"),
    path("billing/payments/", views.admin_payment_list, name="payment_list"),
    path("billing/payments/record/", views.admin_record_payment, name="record_payment"),
    path("billing/settings/", views.admin_gateway_settings, name="gateway_settings"),
    # Property billing config
    path("billing/properties/<uuid:property_pk>/config/", views.admin_property_billing_config, name="property_billing_config"),
    # Recurring charges
    path("billing/leases/<uuid:lease_pk>/charges/", views.admin_recurring_charges, name="recurring_charges"),
    path("billing/charges/<uuid:pk>/edit/", views.admin_recurring_charge_edit, name="recurring_charge_edit"),
    path("billing/charges/<uuid:pk>/delete/", views.admin_recurring_charge_delete, name="recurring_charge_delete"),
    # Utility configuration
    path("billing/utilities/unit/<uuid:unit_pk>/", views.admin_utility_config_unit, name="utility_config_unit"),
    path("billing/utilities/bulk/", views.admin_utility_bulk_set, name="utility_bulk_set"),
    path("billing/utilities/history/", views.admin_utility_rate_history, name="utility_rate_history"),
    # API
    path("billing/api/utility-rate/", views.api_update_variable_rate, name="api_utility_rate"),
]
