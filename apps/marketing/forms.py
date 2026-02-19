from django import forms
from django.forms import inlineformset_factory

from .models import Campaign, CampaignSegment


class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ["name", "subject", "body_html", "body_text", "scheduled_at"]
        widgets = {
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "body_html": forms.Textarea(attrs={"rows": 10}),
        }


class CampaignSegmentForm(forms.ModelForm):
    class Meta:
        model = CampaignSegment
        fields = ["filter_type", "filter_value"]


class CampaignSegmentInlineForm(forms.ModelForm):
    """Form for use within an inline formset for CampaignSegments."""

    filter_value_json = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="JSON-encoded filter value (populated by JavaScript).",
    )

    class Meta:
        model = CampaignSegment
        fields = ["filter_type", "filter_value"]
        widgets = {
            "filter_type": forms.Select(
                attrs={"class": "form-select segment-filter-type"}
            ),
            "filter_value": forms.HiddenInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        filter_type = cleaned_data.get("filter_type")
        filter_value = cleaned_data.get("filter_value")

        if filter_type and filter_type != "all" and not filter_value:
            json_val = cleaned_data.get("filter_value_json")
            if json_val:
                import json

                try:
                    cleaned_data["filter_value"] = json.loads(json_val)
                except (json.JSONDecodeError, TypeError):
                    pass

        if not filter_value:
            cleaned_data["filter_value"] = {}

        return cleaned_data


CampaignSegmentFormSet = inlineformset_factory(
    Campaign,
    CampaignSegment,
    form=CampaignSegmentInlineForm,
    fields=["filter_type", "filter_value"],
    extra=1,
    can_delete=True,
)
