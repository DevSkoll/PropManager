from django.apps import AppConfig


class TenantLifecycleConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tenant_lifecycle"
    verbose_name = "Tenant Lifecycle"
