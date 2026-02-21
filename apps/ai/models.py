"""
AI Gateway models for provider configuration and capabilities.
"""

from django.db import models

from apps.core.models import TimeStampedModel


class AIProvider(TimeStampedModel):
    """
    AI provider configuration storing API keys and model settings.

    Supports OpenAI, Anthropic (Claude), Google Gemini, and LocalAI.
    """

    PROVIDER_CHOICES = [
        ("openai", "OpenAI"),
        ("anthropic", "Anthropic (Claude)"),
        ("google_gemini", "Google Gemini"),
        ("localai", "LocalAI"),
    ]

    name = models.CharField(
        max_length=100,
        help_text="Display name for this provider configuration",
    )
    provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        help_text="AI provider type",
    )
    is_active = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this provider is available for use",
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Use as the default provider for AI requests",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Provider-specific configuration (api_key, model, base_url)",
    )

    class Meta:
        ordering = ["-is_default", "-is_active", "name"]
        verbose_name = "AI Provider"
        verbose_name_plural = "AI Providers"

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        default = " (Default)" if self.is_default else ""
        return f"{self.name} - {self.get_provider_display()} [{status}]{default}"

    def save(self, *args, **kwargs):
        # Ensure only one default provider exists
        if self.is_default and self.is_active:
            AIProvider.objects.filter(is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)

    @property
    def model_name(self):
        """Get the configured model name."""
        return self.config.get("model", "")

    @property
    def has_api_key(self):
        """Check if API key is configured."""
        return bool(self.config.get("api_key"))


class AICapability(TimeStampedModel):
    """
    AI capability that can be enabled for various features.

    Each capability connects to a provider and enables AI functionality
    in different parts of the application.
    """

    CAPABILITY_CHOICES = [
        ("messaging", "AI Response Messages"),
        ("workorders", "AI Work Order Handling"),
        ("agents", "AI Agents"),
    ]

    capability = models.CharField(
        max_length=30,
        choices=CAPABILITY_CHOICES,
        unique=True,
        help_text="Type of AI capability",
    )
    is_enabled = models.BooleanField(
        default=False,
        help_text="Whether this capability is enabled",
    )
    provider = models.ForeignKey(
        AIProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="capabilities",
        help_text="Provider to use for this capability",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Capability-specific configuration",
    )

    class Meta:
        ordering = ["capability"]
        verbose_name = "AI Capability"
        verbose_name_plural = "AI Capabilities"

    def __str__(self):
        status = "Enabled" if self.is_enabled else "Disabled"
        return f"{self.get_capability_display()} [{status}]"

    @property
    def is_available(self):
        """Check if capability is available (enabled with active provider)."""
        return self.is_enabled and self.provider and self.provider.is_active
