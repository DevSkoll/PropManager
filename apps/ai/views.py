"""
AI Gateway admin views for provider and capability management.
"""

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.decorators import admin_required

from .forms import PROVIDER_FORM_MAP, PROVIDER_INFO
from .models import AICapability, AIProvider


@admin_required
def admin_dashboard(request):
    """Main AI Gateway dashboard showing providers and capabilities."""
    providers = AIProvider.objects.all()

    # Build provider cards with configured status
    provider_cards = []
    for provider_key, info in PROVIDER_INFO.items():
        configured = providers.filter(provider=provider_key).first()
        provider_cards.append(
            {
                "key": provider_key,
                "name": info["name"],
                "icon": info["icon"],
                "description": info["description"],
                "color": info["color"],
                "configured": configured,
                "is_active": configured.is_active if configured else False,
                "is_default": configured.is_default if configured else False,
                "model": configured.model_name if configured else None,
            }
        )

    # Get or create capabilities
    capabilities = []
    for cap_key, cap_name in AICapability.CAPABILITY_CHOICES:
        cap, _ = AICapability.objects.get_or_create(
            capability=cap_key,
            defaults={"is_enabled": False},
        )
        capabilities.append(cap)

    context = {
        "provider_cards": provider_cards,
        "capabilities": capabilities,
        "active_providers": providers.filter(is_active=True).count(),
        "total_providers": providers.count(),
    }
    return render(request, "ai/admin_dashboard.html", context)


@admin_required
def admin_provider_create(request, provider=None):
    """Create a new AI provider configuration."""
    if not provider:
        # Show provider selection
        context = {
            "providers": PROVIDER_INFO,
        }
        return render(request, "ai/admin_provider_select.html", context)

    if provider not in PROVIDER_FORM_MAP:
        messages.error(request, f"Unknown provider type: {provider}")
        return redirect("ai_admin:dashboard")

    # Check if provider already exists
    existing = AIProvider.objects.filter(provider=provider).first()
    if existing:
        messages.info(request, f"{PROVIDER_INFO[provider]['name']} is already configured. Editing existing configuration.")
        return redirect("ai_admin:provider_edit", pk=existing.pk)

    FormClass = PROVIDER_FORM_MAP[provider]
    provider_info = PROVIDER_INFO[provider]

    if request.method == "POST":
        form = FormClass(request.POST)
        if form.is_valid():
            instance = form.save()
            messages.success(
                request, f"{provider_info['name']} provider configured successfully."
            )
            return redirect("ai_admin:dashboard")
    else:
        form = FormClass()

    context = {
        "form": form,
        "provider_key": provider,
        "provider_info": provider_info,
        "is_edit": False,
    }
    return render(request, "ai/admin_provider_form.html", context)


@admin_required
def admin_provider_edit(request, pk):
    """Edit an existing AI provider configuration."""
    provider_obj = get_object_or_404(AIProvider, pk=pk)
    FormClass = PROVIDER_FORM_MAP.get(provider_obj.provider)

    if not FormClass:
        messages.error(request, "Unknown provider type.")
        return redirect("ai_admin:dashboard")

    provider_info = PROVIDER_INFO[provider_obj.provider]

    if request.method == "POST":
        form = FormClass(request.POST, instance=provider_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"{provider_info['name']} provider updated.")
            return redirect("ai_admin:dashboard")
    else:
        form = FormClass(instance=provider_obj)

    context = {
        "form": form,
        "provider": provider_obj,
        "provider_key": provider_obj.provider,
        "provider_info": provider_info,
        "is_edit": True,
    }
    return render(request, "ai/admin_provider_form.html", context)


@admin_required
@require_POST
def admin_provider_delete(request, pk):
    """Delete an AI provider configuration."""
    provider_obj = get_object_or_404(AIProvider, pk=pk)
    name = provider_obj.name
    provider_obj.delete()
    messages.success(request, f"Provider '{name}' deleted.")
    return redirect("ai_admin:dashboard")


@admin_required
@require_POST
def admin_provider_test(request, pk):
    """Test connection to an AI provider."""
    provider_obj = get_object_or_404(AIProvider, pk=pk)

    if not provider_obj.has_api_key and provider_obj.provider != "localai":
        return JsonResponse(
            {"success": False, "message": "API key not configured."}
        )

    # Test connection based on provider type
    try:
        success, message = _test_provider_connection(provider_obj)
        return JsonResponse({"success": success, "message": message})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})


def _test_provider_connection(provider: AIProvider) -> tuple[bool, str]:
    """Test connection to a provider. Returns (success, message)."""
    config = provider.config

    if provider.provider == "openai":
        try:
            import openai

            client = openai.OpenAI(api_key=config.get("api_key"))
            # List models to verify connection
            client.models.list()
            return True, "Connection successful"
        except ImportError:
            return False, "OpenAI library not installed"
        except Exception as e:
            return False, str(e)

    elif provider.provider == "anthropic":
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=config.get("api_key"))
            # Simple test request
            client.messages.create(
                model=config.get("model", "claude-3-haiku-20240307"),
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True, "Connection successful"
        except ImportError:
            return False, "Anthropic library not installed"
        except Exception as e:
            return False, str(e)

    elif provider.provider == "google_gemini":
        try:
            import google.generativeai as genai

            genai.configure(api_key=config.get("api_key"))
            model = genai.GenerativeModel(config.get("model", "gemini-pro"))
            model.generate_content("Hi")
            return True, "Connection successful"
        except ImportError:
            return False, "Google Generative AI library not installed"
        except Exception as e:
            return False, str(e)

    elif provider.provider == "localai":
        try:
            import requests

            base_url = config.get("base_url", "http://localhost:8080")
            headers = {}
            if config.get("api_key"):
                headers["Authorization"] = f"Bearer {config['api_key']}"

            response = requests.get(f"{base_url}/v1/models", headers=headers, timeout=10)
            response.raise_for_status()
            return True, "Connection successful"
        except ImportError:
            return False, "Requests library not installed"
        except Exception as e:
            return False, str(e)

    return False, "Unknown provider type"
