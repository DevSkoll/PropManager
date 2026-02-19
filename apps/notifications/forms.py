from django import forms

from apps.accounts.models import User

from .models import (
    CATEGORY_CHOICES,
    CHANNEL_WITH_NONE_CHOICES,
    EVENT_TYPE_CHOICES,
    GroupContact,
    NotificationGroup,
    TenantNotificationPreference,
)


class NotificationGroupForm(forms.ModelForm):
    class Meta:
        model = NotificationGroup
        fields = ["name", "description", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class GroupContactForm(forms.ModelForm):
    class Meta:
        model = GroupContact
        fields = [
            "user",
            "external_name",
            "external_email",
            "external_phone",
            "channel",
            "service_name",
            "webhook_url",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.filter(
            role__in=["admin", "staff"], is_active=True
        )
        self.fields["user"].required = False
        self.fields["user"].empty_label = "— Select a staff user (or leave blank for external) —"
        self.fields["webhook_url"].label = "Webhook URL"

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get("user")
        channel = cleaned_data.get("channel")

        if channel == "webhook":
            # Webhook mode: require service name and URL
            svc_name = cleaned_data.get("service_name", "").strip()
            url = cleaned_data.get("webhook_url", "").strip()

            if not svc_name:
                self.add_error(
                    "service_name", "Webhook contacts must have a service name."
                )
            if not url:
                self.add_error(
                    "webhook_url", "Webhook contacts must have a URL."
                )

            # Clear user and external fields
            cleaned_data["user"] = None
            cleaned_data["external_name"] = ""
            cleaned_data["external_email"] = ""
            cleaned_data["external_phone"] = ""
        elif user:
            # User mode: clear external and webhook fields
            cleaned_data["external_name"] = ""
            cleaned_data["external_email"] = ""
            cleaned_data["external_phone"] = ""
            cleaned_data["service_name"] = ""
            cleaned_data["webhook_url"] = ""
        else:
            # External contact: require name + at least email or phone
            name = cleaned_data.get("external_name", "").strip()
            email = cleaned_data.get("external_email", "").strip()
            phone = cleaned_data.get("external_phone", "").strip()

            cleaned_data["service_name"] = ""
            cleaned_data["webhook_url"] = ""

            if not name:
                self.add_error(
                    "external_name", "External contacts must have a name."
                )
            if not email and not phone:
                raise forms.ValidationError(
                    "External contacts must have at least an email or phone number."
                )

        return cleaned_data


class EventTypeSubscriptionForm(forms.Form):
    event_types = forms.MultipleChoiceField(
        choices=EVENT_TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Subscribe to event types",
    )


class TenantNotificationPreferenceForm(forms.Form):
    """
    Dynamic form: one RadioSelect field per notification category,
    pre-filled from existing preferences.
    """

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant

        # Load existing preferences
        existing = {}
        if tenant:
            for pref in TenantNotificationPreference.objects.filter(tenant=tenant):
                existing[pref.category] = pref.channel

        for value, label in CATEGORY_CHOICES:
            self.fields[value] = forms.ChoiceField(
                choices=CHANNEL_WITH_NONE_CHOICES,
                widget=forms.RadioSelect,
                label=label,
                initial=existing.get(value, "email"),
                required=True,
            )

    def save(self):
        for value, _label in CATEGORY_CHOICES:
            channel = self.cleaned_data.get(value, "email")
            TenantNotificationPreference.objects.update_or_create(
                tenant=self.tenant,
                category=value,
                defaults={"channel": channel},
            )


class SendReminderForm(forms.Form):
    confirm = forms.BooleanField(
        required=True,
        label="I confirm I want to send this payment reminder",
    )
