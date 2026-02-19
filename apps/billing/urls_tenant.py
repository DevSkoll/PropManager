from django.urls import path

from . import views

app_name = "billing_tenant"

urlpatterns = [
    path("billing/", views.tenant_billing_dashboard, name="billing_dashboard"),
    path("billing/invoices/", views.tenant_invoice_list, name="invoice_list"),
    path("billing/<uuid:pk>/", views.tenant_invoice_detail, name="invoice_detail"),
    path("billing/<uuid:pk>/pay/", views.tenant_initiate_payment, name="initiate_payment"),
    path("billing/history/", views.tenant_payment_history, name="payment_history"),
    path("billing/payment/callback/", views.tenant_payment_callback, name="payment_callback"),
    # Webhook (no auth, uses signature verification)
    path("billing/webhook/<str:provider>/", views.tenant_payment_webhook, name="payment_webhook"),
]
