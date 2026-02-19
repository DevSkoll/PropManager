from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("reports/", views.reports_index, name="index"),
    path("reports/rent-roll/", views.rent_roll_report, name="rent_roll"),
    path("reports/aging-receivables/", views.aging_receivables_report, name="aging_receivables"),
    path("reports/payment-history/", views.payment_history_report, name="payment_history"),
    path("reports/workorder-summary/", views.workorder_summary_report, name="workorder_summary"),
]
