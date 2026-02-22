from django.apps import AppConfig


class SetupConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.setup"
    verbose_name = "Setup Wizard"
