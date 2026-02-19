from decimal import Decimal

from django import forms
from django.forms import inlineformset_factory

from apps.accounts.models import User

from .models import PropertyRewardsConfig, StreakRewardTier


class PropertyRewardsConfigForm(forms.ModelForm):
    class Meta:
        model = PropertyRewardsConfig
        fields = [
            "rewards_enabled",
            "streak_reward_enabled",
            "prepayment_reward_enabled",
            "prepayment_threshold_amount",
            "prepayment_reward_amount",
            "auto_apply_rewards",
        ]


class StreakRewardTierForm(forms.ModelForm):
    class Meta:
        model = StreakRewardTier
        fields = ["months_required", "reward_amount", "is_recurring"]


StreakRewardTierFormSet = inlineformset_factory(
    PropertyRewardsConfig,
    StreakRewardTier,
    form=StreakRewardTierForm,
    extra=1,
    can_delete=True,
)


class ManualRewardGrantForm(forms.Form):
    tenant = forms.ModelChoiceField(
        queryset=User.objects.filter(role="tenant").order_by("last_name", "first_name"),
        label="Tenant",
    )
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        label="Reward Amount ($)",
    )
    description = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Reason / Description",
    )


class AdminAdjustBalanceForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Adjustment Amount ($)",
        help_text="Positive to add, negative to deduct.",
    )
    description = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Reason / Description",
    )

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount == 0:
            raise forms.ValidationError("Adjustment amount cannot be zero.")
        return amount


class TenantApplyRewardsForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
        label="Amount to Apply ($)",
    )
    apply_all = forms.BooleanField(
        required=False,
        label="Apply full reward balance",
    )

    def clean(self):
        cleaned_data = super().clean()
        apply_all = cleaned_data.get("apply_all")
        amount = cleaned_data.get("amount")
        if not apply_all and not amount:
            raise forms.ValidationError("Please enter an amount or check 'Apply full reward balance'.")
        return cleaned_data
