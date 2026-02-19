from django import forms
from django.conf import settings

from apps.accounts.models import User

from .models import Announcement, Message, MessageThread


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 3, "placeholder": "Type your message..."}),
        }


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ["title", "body", "property", "is_published"]


class ThreadCreateForm(forms.Form):
    subject = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Message subject",
        }),
    )
    body = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 5,
            "placeholder": "Write your message...",
        }),
    )
    participants = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "8"}),
        required=False,
        help_text="Select one or more recipients.",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.is_admin_user:
            # Admin can message any tenant
            self.fields["participants"].queryset = User.objects.filter(
                role="tenant", is_active=True
            ).order_by("last_name", "first_name")
            self.fields["participants"].required = True
        else:
            # Tenants don't pick participants -- message goes to admins
            del self.fields["participants"]
