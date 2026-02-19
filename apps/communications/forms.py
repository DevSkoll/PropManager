from django import forms

from .models import Announcement, Message


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
