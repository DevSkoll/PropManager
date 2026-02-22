"""
Setup Wizard Views for PropManager first-run configuration.
"""

import json
import logging

from django.contrib import messages
from django.contrib.auth import login
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views import View
from django.views.decorators.http import require_POST

from .forms import (
    AdminAccountForm,
    CSVUploadForm,
    DataImportChoiceForm,
    EmailConfigForm,
    IntegrationSettingsForm,
    PaymentGatewaySelectForm,
    SMSConfigForm,
)
from .models import (
    WIZARD_STEPS,
    CSVImportLog,
    SetupConfiguration,
    get_next_step,
    get_previous_step,
    get_step_index,
    get_wizard_step,
)
from .services.csv_importer import CSVImporter, get_sample_csv_content
from .services.validators import (
    run_database_checks,
    test_email_configuration,
    test_payment_gateway,
    test_sms_configuration,
)

logger = logging.getLogger(__name__)


def setup_redirect(request):
    """Redirect to the appropriate setup step."""
    config = SetupConfiguration.get_instance()

    if config.is_complete:
        return redirect("accounts_admin:admin_dashboard")

    # Auto-detect existing configurations on first access
    # (when steps_completed is empty, indicating fresh setup run)
    if not config.steps_completed:
        _run_auto_detection(config)

    # Find the first incomplete step
    for step in WIZARD_STEPS:
        if not config.is_step_complete(step["key"]):
            return redirect(f"setup:{step['key']}")

    # All steps complete, go to review
    return redirect("setup:review")


def _run_auto_detection(config):
    """
    Run auto-detection to find existing configurations.
    Marks steps as complete if their requirements are already satisfied.
    """
    from .services.auto_detection import auto_detect_existing_configurations

    try:
        detections = auto_detect_existing_configurations()

        for step_key, detection in detections.items():
            if detection.get("is_complete"):
                # Mark as auto-completed with any warnings
                config.mark_step_complete(
                    step_key,
                    skipped=False,
                    warnings=detection.get("warnings", []),
                )
                logger.info(
                    f"Auto-detected {step_key}: {detection.get('details', 'configured')}"
                )
    except Exception as e:
        logger.warning(f"Auto-detection failed: {e}")


class BaseSetupStepView(View):
    """Base class for all setup wizard steps."""

    step_key = None
    template_name = None

    def get_context_data(self, **kwargs):
        """Get common context data for all steps."""
        config = SetupConfiguration.get_instance()
        current_step = get_wizard_step(self.step_key)
        prev_step = get_previous_step(self.step_key)
        next_step = get_next_step(self.step_key)

        # Check if this step was auto-completed (completed without being skipped)
        step_status = config.get_step_status(self.step_key)
        step_auto_completed = (
            step_status is not None
            and not step_status.get("skipped", False)
        )

        return {
            "current_step": current_step,
            "previous_step": prev_step,
            "next_step": next_step,
            "all_steps": WIZARD_STEPS,
            "steps_completed": config.steps_completed,
            "progress_percent": self.calculate_progress(config),
            "step_index": get_step_index(self.step_key) + 1,
            "total_steps": len(WIZARD_STEPS),
            "step_auto_completed": step_auto_completed,
            "step_status": step_status,
            **kwargs,
        }

    def calculate_progress(self, config):
        """Calculate wizard progress percentage."""
        completed = len(config.steps_completed)
        total = len(WIZARD_STEPS)
        return int((completed / total) * 100)

    def mark_complete(self, skipped=False, warnings=None):
        """Mark the current step as complete."""
        config = SetupConfiguration.get_instance()
        config.mark_step_complete(self.step_key, skipped=skipped, warnings=warnings)

    def get_next_url(self):
        """Get the URL for the next step."""
        next_step = get_next_step(self.step_key)
        if next_step:
            return f"setup:{next_step['key']}"
        return "setup:review"


class WelcomeStepView(BaseSetupStepView):
    """Welcome and introduction step."""

    step_key = "welcome"
    template_name = "setup/step_welcome.html"

    def get(self, request):
        from django.conf import settings

        context = self.get_context_data()
        context["site_url"] = settings.SITE_URL
        return render(request, self.template_name, context)

    def post(self, request):
        self.mark_complete()
        return redirect("setup:admin_account")


class AdminAccountStepView(BaseSetupStepView):
    """Admin account creation step."""

    step_key = "admin_account"
    template_name = "setup/step_admin_account.html"

    def get(self, request):
        from apps.accounts.models import User

        admin_exists = User.objects.filter(role="admin", is_superuser=True).exists()
        form = AdminAccountForm()

        context = self.get_context_data(form=form, admin_exists=admin_exists)
        return render(request, self.template_name, context)

    def post(self, request):
        from apps.accounts.models import AdminProfile, User

        action = request.POST.get("action")

        # Check if using existing admin
        if action == "use_existing":
            admin_exists = User.objects.filter(role="admin", is_superuser=True).exists()
            if admin_exists:
                self.mark_complete()
                return redirect("setup:database")
            messages.error(request, "No existing admin account found.")

        form = AdminAccountForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Create admin profile
            AdminProfile.objects.get_or_create(user=user)

            # Log in the new admin
            login(request, user)

            self.mark_complete()
            messages.success(request, f"Admin account '{user.username}' created successfully!")
            return redirect("setup:database")

        admin_exists = User.objects.filter(role="admin", is_superuser=True).exists()
        context = self.get_context_data(form=form, admin_exists=admin_exists)
        return render(request, self.template_name, context)


class DatabaseCheckStepView(BaseSetupStepView):
    """Database connectivity verification step."""

    step_key = "database"
    template_name = "setup/step_database.html"

    def get(self, request):
        checks = run_database_checks()
        all_passed = all(c["passed"] for c in checks)

        context = self.get_context_data(checks=checks, all_passed=all_passed)
        return render(request, self.template_name, context)

    def post(self, request):
        checks = run_database_checks()
        all_passed = all(c["passed"] for c in checks)

        if all_passed:
            self.mark_complete()
            return redirect("setup:communications")

        context = self.get_context_data(
            checks=checks,
            all_passed=False,
            error="Please resolve database issues before continuing.",
        )
        return render(request, self.template_name, context)


class CommunicationsStepView(BaseSetupStepView):
    """Email and SMS configuration step."""

    step_key = "communications"
    template_name = "setup/step_communications.html"

    def get(self, request):
        email_form = EmailConfigForm(prefix="email")
        sms_form = SMSConfigForm(prefix="sms")

        context = self.get_context_data(
            email_form=email_form,
            sms_form=sms_form,
        )
        return render(request, self.template_name, context)

    def post(self, request):
        action = request.POST.get("action")

        if action == "skip":
            self.mark_complete(
                skipped=True,
                warnings=[
                    "No email or SMS provider configured",
                    "Notifications will not be sent until configured",
                ],
            )
            return redirect("setup:payment")

        email_form = EmailConfigForm(request.POST, prefix="email")
        sms_form = SMSConfigForm(request.POST, prefix="sms")

        warnings = []
        email_configured = False
        sms_configured = False

        # Process email configuration
        if email_form.is_valid():
            email_data = email_form.cleaned_data
            if email_data.get("email_host"):
                try:
                    from apps.notifications.models import EmailConfig

                    EmailConfig.objects.update_or_create(
                        is_active=True,
                        defaults={
                            "email_host": email_data["email_host"],
                            "email_port": email_data["email_port"],
                            "email_host_user": email_data["email_host_user"],
                            "email_host_password": email_data["email_host_password"],
                            "default_from_email": email_data["default_from_email"],
                            "email_use_tls": email_data.get("email_use_tls", True),
                            "email_use_ssl": email_data.get("email_use_ssl", False),
                        },
                    )
                    email_configured = True
                except Exception as e:
                    logger.error(f"Failed to save email config: {e}")
                    warnings.append(f"Email configuration error: {str(e)}")
            else:
                warnings.append("Email not configured")
        else:
            warnings.append("Email configuration has errors")

        # Process SMS configuration
        if sms_form.is_valid():
            sms_data = sms_form.cleaned_data
            if sms_data.get("account_sid"):
                try:
                    from apps.notifications.models import SMSConfig

                    SMSConfig.objects.update_or_create(
                        is_active=True,
                        defaults={
                            "account_sid": sms_data["account_sid"],
                            "auth_token": sms_data["auth_token"],
                            "phone_number": sms_data["phone_number"],
                        },
                    )
                    sms_configured = True
                except Exception as e:
                    logger.error(f"Failed to save SMS config: {e}")
                    warnings.append(f"SMS configuration error: {str(e)}")
            else:
                warnings.append("SMS not configured")
        else:
            warnings.append("SMS configuration has errors")

        if email_configured or sms_configured:
            self.mark_complete(warnings=warnings if warnings else None)
            return redirect("setup:payment")

        # Neither configured - show validation
        context = self.get_context_data(
            email_form=email_form,
            sms_form=sms_form,
            error="Please configure at least one communication provider or skip this step.",
        )
        return render(request, self.template_name, context)


class PaymentGatewayStepView(BaseSetupStepView):
    """Payment gateway configuration step."""

    step_key = "payment"
    template_name = "setup/step_payment.html"

    def get(self, request):
        from apps.billing.models import PaymentGatewayConfig

        existing_gateways = PaymentGatewayConfig.objects.filter(is_active=True)
        form = PaymentGatewaySelectForm()

        context = self.get_context_data(
            form=form,
            existing_gateways=existing_gateways,
        )
        return render(request, self.template_name, context)

    def post(self, request):
        action = request.POST.get("action")

        if action == "skip":
            self.mark_complete(
                skipped=True,
                warnings=[
                    "No payment gateway configured",
                    "Online rent payments will not be available",
                ],
            )
            return redirect("setup:integrations")

        form = PaymentGatewaySelectForm(request.POST)
        if form.is_valid():
            provider = form.cleaned_data["provider"]
            display_name = form.cleaned_data.get("display_name") or provider.title()

            # Get provider-specific config from POST
            config_data = self._extract_provider_config(request.POST, provider)

            try:
                from apps.billing.models import PaymentGatewayConfig

                # Deactivate other gateways
                PaymentGatewayConfig.objects.filter(is_default=True).update(is_default=False)

                PaymentGatewayConfig.objects.update_or_create(
                    provider=provider,
                    defaults={
                        "display_name": display_name,
                        "is_active": True,
                        "is_default": True,
                        "config": config_data,
                    },
                )

                self.mark_complete()
                return redirect("setup:integrations")

            except Exception as e:
                logger.error(f"Failed to save payment gateway: {e}")
                messages.error(request, f"Failed to save configuration: {str(e)}")

        context = self.get_context_data(form=form)
        return render(request, self.template_name, context)

    def _extract_provider_config(self, post_data, provider):
        """Extract provider-specific configuration from POST data."""
        config = {}
        prefix = f"{provider}_"

        for key, value in post_data.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):]
                config[config_key] = value

        return config


class IntegrationsStepView(BaseSetupStepView):
    """Optional integrations configuration step (AI, Weather, Rewards)."""

    step_key = "integrations"
    template_name = "setup/step_integrations.html"

    def get(self, request):
        form = IntegrationSettingsForm()
        context = self.get_context_data(form=form)
        return render(request, self.template_name, context)

    def post(self, request):
        action = request.POST.get("action")

        if action == "skip":
            self.mark_complete(skipped=True)
            return redirect("setup:import")

        form = IntegrationSettingsForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            warnings = []

            # Configure AI provider
            if data.get("enable_ai") and data.get("ai_provider") and data.get("ai_api_key"):
                try:
                    from apps.ai.models import AIProvider

                    AIProvider.objects.update_or_create(
                        provider=data["ai_provider"],
                        defaults={
                            "api_key": data["ai_api_key"],
                            "is_active": True,
                        },
                    )
                except Exception as e:
                    logger.error(f"Failed to save AI provider: {e}")
                    warnings.append(f"AI configuration error: {str(e)}")

            # Configure Weather
            if data.get("enable_weather") and data.get("weather_api_key"):
                try:
                    from apps.weather.models import WeatherConfig

                    WeatherConfig.objects.update_or_create(
                        is_active=True,
                        defaults={
                            "api_key": data["weather_api_key"],
                            "default_unit": "imperial",
                        },
                    )
                except Exception as e:
                    logger.error(f"Failed to save weather config: {e}")
                    warnings.append(f"Weather configuration error: {str(e)}")

            # Enable Rewards (if model exists)
            if data.get("enable_rewards"):
                # Rewards is enabled by default in the app, no config needed
                pass

            self.mark_complete(warnings=warnings if warnings else None)
            return redirect("setup:import")

        context = self.get_context_data(form=form)
        return render(request, self.template_name, context)


class DataImportStepView(BaseSetupStepView):
    """Data import or demo data loading step."""

    step_key = "import"
    template_name = "setup/step_import.html"

    def get(self, request):
        form = DataImportChoiceForm()
        context = self.get_context_data(
            form=form,
            sample_formats=self._get_sample_formats(),
        )
        return render(request, self.template_name, context)

    def post(self, request):
        action = request.POST.get("action")
        import_choice = request.POST.get("import_choice", "skip")

        if action == "skip" or import_choice == "skip":
            self.mark_complete(skipped=True)
            return redirect("setup:review")

        if import_choice == "demo":
            try:
                from django.core.management import call_command

                call_command("seed_dev_data", verbosity=0)
                self.mark_complete(
                    warnings=["Demo data loaded - suitable for testing only"]
                )
                messages.success(request, "Demo data loaded successfully!")
                return redirect("setup:review")
            except Exception as e:
                logger.error(f"Failed to load demo data: {e}")
                messages.error(request, f"Failed to load demo data: {str(e)}")

        if import_choice == "import":
            return self._handle_csv_import(request)

        form = DataImportChoiceForm(request.POST)
        context = self.get_context_data(
            form=form,
            sample_formats=self._get_sample_formats(),
        )
        return render(request, self.template_name, context)

    def _handle_csv_import(self, request):
        """Handle CSV file imports."""
        results = []
        warnings = []

        for import_type in ["properties", "units", "tenants"]:
            file = request.FILES.get(f"{import_type}_csv")
            if file:
                try:
                    content = file.read().decode("utf-8")
                    importer = CSVImporter(import_type, content, request.user)
                    result = importer.import_data()

                    # Log the import
                    CSVImportLog.objects.create(
                        import_type=import_type,
                        status="completed" if not result["errors"] else "failed",
                        file_name=file.name,
                        total_rows=result["created"] + result["updated"] + len(result["errors"]),
                        successful_rows=result["created"] + result["updated"],
                        failed_rows=len(result["errors"]),
                        errors=result["errors"],
                        warnings=result["warnings"],
                        imported_by=request.user if request.user.is_authenticated else None,
                    )

                    results.append({
                        "type": import_type,
                        "created": result["created"],
                        "updated": result["updated"],
                        "errors": len(result["errors"]),
                    })

                    if result["warnings"]:
                        warnings.extend([w["warning"] for w in result["warnings"]])

                except Exception as e:
                    logger.error(f"CSV import failed for {import_type}: {e}")
                    results.append({
                        "type": import_type,
                        "error": str(e),
                    })

        if results:
            self.mark_complete(warnings=warnings if warnings else None)

            # Create summary message
            summary_parts = []
            for r in results:
                if "error" in r:
                    summary_parts.append(f"{r['type']}: Error - {r['error']}")
                else:
                    summary_parts.append(
                        f"{r['type']}: {r['created']} created, {r['updated']} updated"
                    )

            messages.success(request, "Import complete: " + "; ".join(summary_parts))
            return redirect("setup:review")

        messages.error(request, "Please upload at least one CSV file or skip this step.")
        form = DataImportChoiceForm(initial={"import_choice": "import"})
        context = self.get_context_data(
            form=form,
            sample_formats=self._get_sample_formats(),
        )
        return render(request, self.template_name, context)

    def _get_sample_formats(self):
        """Get sample CSV formats for display."""
        return {
            "properties": {
                "headers": [
                    "name",
                    "property_type",
                    "address_line1",
                    "city",
                    "state",
                    "zip_code",
                    "total_units",
                ],
                "sample_row": [
                    "Sunset Apartments",
                    "apartment",
                    "100 Sunset Blvd",
                    "Los Angeles",
                    "CA",
                    "90028",
                    "10",
                ],
            },
            "units": {
                "headers": [
                    "property_name",
                    "unit_number",
                    "bedrooms",
                    "bathrooms",
                    "square_feet",
                    "base_rent",
                    "status",
                ],
                "sample_row": [
                    "Sunset Apartments",
                    "101",
                    "2",
                    "1.5",
                    "850",
                    "1500.00",
                    "vacant",
                ],
            },
            "tenants": {
                "headers": [
                    "email",
                    "first_name",
                    "last_name",
                    "phone_number",
                    "unit_number",
                    "property_name",
                    "lease_start",
                    "monthly_rent",
                ],
                "sample_row": [
                    "john@example.com",
                    "John",
                    "Doe",
                    "+15551234567",
                    "101",
                    "Sunset Apartments",
                    "2024-01-01",
                    "1500.00",
                ],
            },
        }


class ReviewCompleteStepView(BaseSetupStepView):
    """Review configuration and complete setup step."""

    step_key = "review"
    template_name = "setup/step_review.html"

    def get(self, request):
        config = SetupConfiguration.get_instance()
        summary = self._build_summary()

        # Calculate warnings and skipped counts
        warnings_count = sum(
            len(s.get("warnings", [])) for s in config.steps_completed.values()
        )
        skipped_count = sum(
            1 for s in config.steps_completed.values() if s.get("skipped")
        )

        context = self.get_context_data(
            summary=summary,
            warnings_count=warnings_count,
            skipped_count=skipped_count,
        )
        return render(request, self.template_name, context)

    def post(self, request):
        config = SetupConfiguration.get_instance()

        # Finalize setup
        user = request.user if request.user.is_authenticated else None
        config.finalize(user)

        # Ensure user is logged in
        if not request.user.is_authenticated:
            from apps.accounts.models import User

            admin_user = User.objects.filter(role="admin", is_superuser=True).first()
            if admin_user:
                login(request, admin_user)

        messages.success(
            request,
            "Setup complete! Welcome to PropManager. Your property management system is ready to use.",
        )
        return redirect("accounts_admin:admin_dashboard")

    def _build_summary(self):
        """Build a summary of all configurations."""
        from apps.accounts.models import User
        from apps.properties.models import Property, Unit

        summary = {
            "admin_count": User.objects.filter(role="admin").count(),
            "staff_count": User.objects.filter(role="staff").count(),
            "tenant_count": User.objects.filter(role="tenant").count(),
            "property_count": Property.objects.count(),
            "unit_count": Unit.objects.count(),
            "email_configured": False,
            "sms_configured": False,
            "payment_gateways": 0,
            "ai_providers": 0,
            "weather_configured": False,
        }

        # Check communications
        try:
            from apps.notifications.models import EmailConfig, SMSConfig

            summary["email_configured"] = EmailConfig.objects.filter(is_active=True).exists()
            summary["sms_configured"] = SMSConfig.objects.filter(is_active=True).exists()
        except Exception:
            pass

        # Check payment gateways
        try:
            from apps.billing.models import PaymentGatewayConfig

            summary["payment_gateways"] = PaymentGatewayConfig.objects.filter(
                is_active=True
            ).count()
        except Exception:
            pass

        # Check AI providers
        try:
            from apps.ai.models import AIProvider

            summary["ai_providers"] = AIProvider.objects.filter(is_active=True).count()
        except Exception:
            pass

        # Check weather config
        try:
            from apps.weather.models import WeatherConfig

            summary["weather_configured"] = WeatherConfig.objects.filter(
                is_active=True
            ).exists()
        except Exception:
            pass

        return summary


# HTMX/AJAX endpoints for testing configurations


@require_POST
def test_email_config(request):
    """Test email configuration via AJAX."""
    config = {
        "email_host": request.POST.get("email-email_host"),
        "email_port": int(request.POST.get("email-email_port", 587)),
        "email_host_user": request.POST.get("email-email_host_user"),
        "email_host_password": request.POST.get("email-email_host_password"),
        "default_from_email": request.POST.get("email-default_from_email"),
        "email_use_tls": request.POST.get("email-email_use_tls") == "on",
        "email_use_ssl": request.POST.get("email-email_use_ssl") == "on",
    }

    result = test_email_configuration(config)
    return JsonResponse(result)


@require_POST
def test_sms_config(request):
    """Test SMS configuration via AJAX."""
    config = {
        "account_sid": request.POST.get("sms-account_sid"),
        "auth_token": request.POST.get("sms-auth_token"),
        "phone_number": request.POST.get("sms-phone_number"),
    }

    result = test_sms_configuration(config)
    return JsonResponse(result)


@require_POST
def test_payment_gateway_config(request):
    """Test payment gateway configuration via AJAX."""
    provider = request.POST.get("provider")
    config_data = {}

    # Extract provider-specific config
    prefix = f"{provider}_"
    for key, value in request.POST.items():
        if key.startswith(prefix):
            config_data[key[len(prefix):]] = value

    result = test_payment_gateway(provider, config_data)
    return JsonResponse(result)


@require_POST
def preview_csv(request):
    """Preview CSV file contents via AJAX."""
    import_type = request.POST.get("import_type")
    file = request.FILES.get("csv_file")

    if not file:
        return JsonResponse({"error": "No file uploaded"}, status=400)

    try:
        content = file.read().decode("utf-8")
        importer = CSVImporter(import_type, content)
        preview_data = importer.preview(limit=5)
        return JsonResponse(preview_data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def download_sample_csv(request, import_type):
    """Download sample CSV template."""
    content = get_sample_csv_content(import_type)
    if not content:
        return HttpResponse("Unknown import type", status=404)

    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="sample_{import_type}.csv"'
    return response
