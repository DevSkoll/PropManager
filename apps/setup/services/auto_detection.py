"""
Auto-detection service for existing configurations.

Scans the database for pre-existing configurations and returns
detection results to auto-complete setup wizard steps.
"""

import logging

from .validators import run_database_checks

logger = logging.getLogger(__name__)


def auto_detect_existing_configurations():
    """
    Scan for existing configurations and return detection results.

    Called on first wizard access when steps_completed is empty.
    This allows the wizard to skip steps that are already configured
    on existing deployments.

    Returns:
        dict mapping step_key -> {is_complete: bool, warnings: list, details: str}
    """
    return {
        "admin_account": _check_existing_admin(),
        "database": _check_database_connectivity(),
        "communications": _check_existing_communications(),
        "payment": _check_existing_payment_gateway(),
        "integrations": _check_existing_integrations(),
        "import": _check_existing_data(),
    }


def _check_existing_admin():
    """Check for existing administrator account."""
    try:
        from apps.accounts.models import User

        admin_count = User.objects.filter(role="admin", is_superuser=True).count()

        if admin_count > 0:
            admin = User.objects.filter(role="admin", is_superuser=True).first()
            return {
                "is_complete": True,
                "warnings": [],
                "details": f"Found {admin_count} admin user(s): {admin.username}",
            }

        return {
            "is_complete": False,
            "warnings": [],
            "details": "No admin users found",
        }
    except Exception as e:
        logger.warning(f"Admin check failed: {e}")
        return {
            "is_complete": False,
            "warnings": [f"Could not check admin users: {str(e)}"],
            "details": "Check failed",
        }


def _check_database_connectivity():
    """Check database connectivity and required tables."""
    try:
        checks = run_database_checks()
        all_passed = all(c["passed"] for c in checks)

        if all_passed:
            return {
                "is_complete": True,
                "warnings": [],
                "details": f"All {len(checks)} database checks passed",
            }

        failed_checks = [c["name"] for c in checks if not c["passed"]]
        return {
            "is_complete": False,
            "warnings": [f"Failed: {', '.join(failed_checks)}"],
            "details": f"{len(failed_checks)} check(s) failed",
        }
    except Exception as e:
        logger.warning(f"Database check failed: {e}")
        return {
            "is_complete": False,
            "warnings": [f"Database check error: {str(e)}"],
            "details": "Check failed",
        }


def _check_existing_communications():
    """Check for existing email or SMS configuration."""
    try:
        from apps.notifications.models import EmailConfig, SMSConfig

        warnings = []
        details_parts = []

        # Check email
        email_config = EmailConfig.objects.filter(is_active=True).first()
        email_configured = False
        if email_config:
            # Verify it has essential fields
            if email_config.email_host and email_config.default_from_email:
                email_configured = True
                details_parts.append(f"Email: {email_config.email_host}")
            else:
                warnings.append("Email config exists but is incomplete")

        # Check SMS
        sms_config = SMSConfig.objects.filter(is_active=True).first()
        sms_configured = False
        if sms_config:
            # Verify it has essential fields
            if sms_config.account_sid and sms_config.auth_token:
                sms_configured = True
                details_parts.append("SMS: Twilio")
            else:
                warnings.append("SMS config exists but is incomplete")

        if email_configured or sms_configured:
            if not email_configured:
                warnings.append("Only SMS configured, no email")
            if not sms_configured:
                warnings.append("Only email configured, no SMS")

            return {
                "is_complete": True,
                "warnings": warnings,
                "details": ", ".join(details_parts) if details_parts else "Configured",
            }

        return {
            "is_complete": False,
            "warnings": warnings,
            "details": "No active email or SMS configuration",
        }
    except Exception as e:
        logger.warning(f"Communications check failed: {e}")
        return {
            "is_complete": False,
            "warnings": [f"Could not check communications: {str(e)}"],
            "details": "Check failed",
        }


def _check_existing_payment_gateway():
    """Check for existing payment gateway configuration."""
    try:
        from apps.billing.models import PaymentGatewayConfig

        active_gateways = PaymentGatewayConfig.objects.filter(is_active=True)
        count = active_gateways.count()

        if count > 0:
            gateway_names = [g.display_name or g.provider for g in active_gateways[:3]]
            return {
                "is_complete": True,
                "warnings": [],
                "details": f"{count} gateway(s): {', '.join(gateway_names)}",
            }

        return {
            "is_complete": False,
            "warnings": [],
            "details": "No active payment gateways",
        }
    except Exception as e:
        logger.warning(f"Payment gateway check failed: {e}")
        return {
            "is_complete": False,
            "warnings": [f"Could not check payment gateways: {str(e)}"],
            "details": "Check failed",
        }


def _check_existing_integrations():
    """Check for existing AI, Weather, or Rewards configuration."""
    try:
        warnings = []
        details_parts = []

        # Check AI providers
        try:
            from apps.ai.models import AIProvider

            ai_count = AIProvider.objects.filter(is_active=True).count()
            if ai_count > 0:
                details_parts.append(f"AI: {ai_count} provider(s)")
        except Exception:
            pass

        # Check Weather config
        try:
            from apps.weather.models import WeatherMonitorConfig

            weather_active = WeatherMonitorConfig.objects.filter(is_active=True).exists()
            if weather_active:
                details_parts.append("Weather: Enabled")
        except Exception:
            # Try alternate model name
            try:
                from apps.weather.models import WeatherConfig

                weather_active = WeatherConfig.objects.filter(is_active=True).exists()
                if weather_active:
                    details_parts.append("Weather: Enabled")
            except Exception:
                pass

        # Check Rewards config
        try:
            from apps.rewards.models import PropertyRewardsConfig

            rewards_enabled = PropertyRewardsConfig.objects.filter(
                rewards_enabled=True
            ).exists()
            if rewards_enabled:
                details_parts.append("Rewards: Enabled")
        except Exception:
            pass

        if details_parts:
            return {
                "is_complete": True,
                "warnings": warnings,
                "details": ", ".join(details_parts),
            }

        return {
            "is_complete": False,
            "warnings": [],
            "details": "No integrations configured",
        }
    except Exception as e:
        logger.warning(f"Integrations check failed: {e}")
        return {
            "is_complete": False,
            "warnings": [f"Could not check integrations: {str(e)}"],
            "details": "Check failed",
        }


def _check_existing_data():
    """Check if properties, units, or tenants exist."""
    try:
        from apps.accounts.models import User
        from apps.properties.models import Property, Unit

        details_parts = []

        property_count = Property.objects.count()
        if property_count > 0:
            details_parts.append(f"{property_count} properties")

        unit_count = Unit.objects.count()
        if unit_count > 0:
            details_parts.append(f"{unit_count} units")

        tenant_count = User.objects.filter(role="tenant").count()
        if tenant_count > 0:
            details_parts.append(f"{tenant_count} tenants")

        if details_parts:
            return {
                "is_complete": True,
                "warnings": [],
                "details": ", ".join(details_parts),
            }

        return {
            "is_complete": False,
            "warnings": [],
            "details": "No data imported yet",
        }
    except Exception as e:
        logger.warning(f"Data check failed: {e}")
        return {
            "is_complete": False,
            "warnings": [f"Could not check existing data: {str(e)}"],
            "details": "Check failed",
        }
