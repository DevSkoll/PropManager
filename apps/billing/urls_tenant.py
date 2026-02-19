from django.urls import path

from . import views

app_name = "billing_tenant"

urlpatterns = [
    path("billing/", views.tenant_billing_dashboard, name="billing_dashboard"),
    path("billing/invoices/", views.tenant_invoice_list, name="invoice_list"),
    path("billing/<uuid:pk>/", views.tenant_invoice_detail, name="invoice_detail"),
    path("billing/history/", views.tenant_payment_history, name="payment_history"),
]
