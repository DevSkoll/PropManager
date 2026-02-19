from django.urls import path

from . import views

app_name = "billing_admin"

urlpatterns = [
    path("billing/invoices/", views.invoice_list, name="invoice_list"),
]
