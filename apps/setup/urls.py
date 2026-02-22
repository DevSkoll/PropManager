from django.urls import path

from . import views

app_name = "setup"

urlpatterns = [
    # Main wizard flow
    path("", views.setup_redirect, name="index"),
    path("welcome/", views.WelcomeStepView.as_view(), name="welcome"),
    path("admin-account/", views.AdminAccountStepView.as_view(), name="admin_account"),
    path("database/", views.DatabaseCheckStepView.as_view(), name="database"),
    path("communications/", views.CommunicationsStepView.as_view(), name="communications"),
    path("payment/", views.PaymentGatewayStepView.as_view(), name="payment"),
    path("integrations/", views.IntegrationsStepView.as_view(), name="integrations"),
    path("import/", views.DataImportStepView.as_view(), name="import"),
    path("review/", views.ReviewCompleteStepView.as_view(), name="review"),
    # HTMX/AJAX endpoints for testing
    path("test-email/", views.test_email_config, name="test_email"),
    path("test-sms/", views.test_sms_config, name="test_sms"),
    path("test-gateway/", views.test_payment_gateway_config, name="test_gateway"),
    path("preview-csv/", views.preview_csv, name="preview_csv"),
    # Sample CSV downloads
    path(
        "download-sample/<str:import_type>/",
        views.download_sample_csv,
        name="download_sample_csv",
    ),
]
