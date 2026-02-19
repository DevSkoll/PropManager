from django.urls import path

from . import views

app_name = "billing_admin"

urlpatterns = [
    path("billing/invoices/", views.admin_invoice_list, name="invoice_list"),
    path("billing/invoices/create/", views.admin_invoice_create, name="invoice_create"),
    path("billing/invoices/generate/", views.admin_invoice_generate_batch, name="invoice_generate_batch"),
    path("billing/invoices/<uuid:pk>/", views.admin_invoice_detail, name="invoice_detail"),
    path("billing/payments/", views.admin_payment_list, name="payment_list"),
    path("billing/payments/record/", views.admin_record_payment, name="record_payment"),
    path("billing/settings/", views.admin_gateway_settings, name="gateway_settings"),
]
