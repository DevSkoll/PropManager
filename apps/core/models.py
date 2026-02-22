import uuid
from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class AuditMixin(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated",
    )

    class Meta:
        abstract = True


class SystemSettings(models.Model):
    """
    System-wide configuration settings.
    Singleton model - only one instance should exist.
    """
    # External API Keys
    openweathermap_api_key = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="OpenWeatherMap API key for weather monitoring features"
    )
    
    # Timestamps
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="system_settings_updates"
    )
    
    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"
    
    def __str__(self):
        return "System Settings"
    
    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance."""
        from django.core.cache import cache
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings
    
    @classmethod
    def get_openweathermap_api_key(cls):
        """Get OpenWeatherMap API key with caching."""
        from django.core.cache import cache
        cache_key = "system_settings_owm_api_key"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        settings = cls.get_settings()
        key = settings.openweathermap_api_key
        cache.set(cache_key, key, 300)  # Cache for 5 minutes
        return key
    
    def save(self, *args, **kwargs):
        """Ensure only one instance exists and clear cache on save."""
        from django.core.cache import cache
        self.pk = 1
        super().save(*args, **kwargs)
        # Clear cache when settings are updated
        cache.delete("system_settings_owm_api_key")
    
    def delete(self, *args, **kwargs):
        """Prevent deletion of the singleton."""
        pass
