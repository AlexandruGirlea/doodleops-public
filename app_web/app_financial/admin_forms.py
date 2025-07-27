from django import forms

from app_financial.admin_widgets import PrettyJSONWidget
from app_financial.models import StripeEvent, CustomerCreditsRemoved
from common.redis_logic.redis_utils import (
    get_remaining_credits_bought, get_remaining_monthly_subscription_credits
)


class StripeEventAdminForm(forms.ModelForm):
    class Meta:
        model = StripeEvent
        fields = "__all__"
        widgets = {
            "event_object": PrettyJSONWidget(attrs={"rows": 20, "cols": 80}),
        }


class CustomerCreditsRemovedForm(forms.ModelForm):
    class Meta:
        model = CustomerCreditsRemoved
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        credits = cleaned_data.get("credits")
        removal_type = cleaned_data.get("removal_type")
        user = cleaned_data.get("user")

        if credits is None or not isinstance(credits, int) or credits <= 0:
            self.add_error("credits", "Credits must be a positive number.")
        elif not user:
            self.add_error("user", "User is required.")

        # Perform additional checks only if removal_type is 'bought'
        if removal_type == "bought":
            remaining_credits_bought_directly = sum(
                get_remaining_credits_bought(username=user.username).values()
            )
            if remaining_credits_bought_directly < credits:
                error_msg = (
                    "User does not have enough credits to remove. "
                    f"User has {remaining_credits_bought_directly} "
                    "credits bought directly."
                )
                self.add_error(None, error_msg)

        elif removal_type == "subscription":
            remaining_monthly_subscription_credits = (
                get_remaining_monthly_subscription_credits(
                    username=user.username
                )
            )

            if remaining_monthly_subscription_credits < credits:
                error_msg = (
                    "User does not have enough credits to remove. "
                    f"User has {remaining_monthly_subscription_credits} "
                    "monthly subscription credits."
                )
                self.add_error(None, error_msg)

        return cleaned_data
