from django import forms

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
