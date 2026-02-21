"""
Forms for AI provider configuration.
"""

from django import forms

from .models import AIProvider


class AIProviderBaseForm(forms.ModelForm):
    """Base form for AI provider configuration."""

    class Meta:
        model = AIProvider
        fields = ["name", "is_active", "is_default"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class OpenAIForm(AIProviderBaseForm):
    """Form for OpenAI provider configuration."""

    api_key = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "off"},
            render_value=True,
        ),
        required=True,
        help_text="Your OpenAI API key (starts with sk-)",
    )
    model = forms.ChoiceField(
        choices=[
            ("gpt-4o", "GPT-4o (Latest)"),
            ("gpt-4-turbo", "GPT-4 Turbo"),
            ("gpt-4", "GPT-4"),
            ("gpt-3.5-turbo", "GPT-3.5 Turbo"),
        ],
        initial="gpt-4o",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.config:
            self.fields["api_key"].initial = self.instance.config.get("api_key", "")
            self.fields["model"].initial = self.instance.config.get("model", "gpt-4o")

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.provider = "openai"
        instance.config = {
            "api_key": self.cleaned_data["api_key"],
            "model": self.cleaned_data["model"],
        }
        if commit:
            instance.save()
        return instance


class AnthropicForm(AIProviderBaseForm):
    """Form for Anthropic (Claude) provider configuration."""

    api_key = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "off"},
            render_value=True,
        ),
        required=True,
        help_text="Your Anthropic API key",
    )
    model = forms.ChoiceField(
        choices=[
            ("claude-sonnet-4-20250514", "Claude Sonnet 4 (Latest)"),
            ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet"),
            ("claude-3-opus-20240229", "Claude 3 Opus"),
            ("claude-3-haiku-20240307", "Claude 3 Haiku"),
        ],
        initial="claude-sonnet-4-20250514",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.config:
            self.fields["api_key"].initial = self.instance.config.get("api_key", "")
            self.fields["model"].initial = self.instance.config.get(
                "model", "claude-sonnet-4-20250514"
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.provider = "anthropic"
        instance.config = {
            "api_key": self.cleaned_data["api_key"],
            "model": self.cleaned_data["model"],
        }
        if commit:
            instance.save()
        return instance


class GeminiForm(AIProviderBaseForm):
    """Form for Google Gemini provider configuration."""

    api_key = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "off"},
            render_value=True,
        ),
        required=True,
        help_text="Your Google AI API key",
    )
    model = forms.ChoiceField(
        choices=[
            ("gemini-2.0-flash", "Gemini 2.0 Flash (Latest)"),
            ("gemini-1.5-pro", "Gemini 1.5 Pro"),
            ("gemini-1.5-flash", "Gemini 1.5 Flash"),
            ("gemini-pro", "Gemini Pro"),
        ],
        initial="gemini-2.0-flash",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.config:
            self.fields["api_key"].initial = self.instance.config.get("api_key", "")
            self.fields["model"].initial = self.instance.config.get(
                "model", "gemini-2.0-flash"
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.provider = "google_gemini"
        instance.config = {
            "api_key": self.cleaned_data["api_key"],
            "model": self.cleaned_data["model"],
        }
        if commit:
            instance.save()
        return instance


class LocalAIForm(AIProviderBaseForm):
    """Form for LocalAI (self-hosted) provider configuration."""

    base_url = forms.URLField(
        initial="http://localhost:8080",
        widget=forms.URLInput(attrs={"class": "form-control"}),
        help_text="Base URL for your LocalAI server (e.g., http://localhost:8080)",
    )
    api_key = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "off"},
            render_value=True,
        ),
        required=False,
        help_text="API key (optional, if required by your LocalAI setup)",
    )
    model = forms.CharField(
        initial="gpt-3.5-turbo",
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text="Model name configured in LocalAI",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.config:
            self.fields["base_url"].initial = self.instance.config.get(
                "base_url", "http://localhost:8080"
            )
            self.fields["api_key"].initial = self.instance.config.get("api_key", "")
            self.fields["model"].initial = self.instance.config.get(
                "model", "gpt-3.5-turbo"
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.provider = "localai"
        instance.config = {
            "base_url": self.cleaned_data["base_url"],
            "api_key": self.cleaned_data["api_key"],
            "model": self.cleaned_data["model"],
        }
        if commit:
            instance.save()
        return instance


# Map provider types to their forms
PROVIDER_FORM_MAP = {
    "openai": OpenAIForm,
    "anthropic": AnthropicForm,
    "google_gemini": GeminiForm,
    "localai": LocalAIForm,
}

# Provider display info for the dashboard
PROVIDER_INFO = {
    "openai": {
        "name": "OpenAI",
        "icon": "bi-lightning-charge",
        "description": "GPT-4, GPT-3.5-turbo, and more",
        "color": "success",
    },
    "anthropic": {
        "name": "Anthropic",
        "icon": "bi-stars",
        "description": "Claude 3 Opus, Sonnet, Haiku",
        "color": "warning",
    },
    "google_gemini": {
        "name": "Google Gemini",
        "icon": "bi-google",
        "description": "Gemini Pro, Gemini Flash",
        "color": "primary",
    },
    "localai": {
        "name": "LocalAI",
        "icon": "bi-hdd-network",
        "description": "Self-hosted, OpenAI-compatible",
        "color": "secondary",
    },
}
