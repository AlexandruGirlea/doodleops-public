from django import forms
from django.db import IntegrityError
from django.contrib.auth.forms import UserCreationForm

from app_users.models import CustomUser
from common.normalize import get_normalized_email


class CustomUserCreationForm(UserCreationForm):
    """This only creates a user, it does not update it."""

    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = (
            "username",
            "email",
            "password1",
            "password2",
            "stripe_customer_id",
        )

    def save(self, commit=True) -> tuple[CustomUser, bool]:
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.normalized_email = get_normalized_email(user.email)

        if commit:
            defaults = {"username": user.username, "password": user.password}

            existing_user, created = CustomUser.objects.get_or_create(
                email=user.email, defaults=defaults
            )

            if created:
                for field in [
                    f.name
                    for f in CustomUser._meta.fields
                    if f.name not in ["id"]
                ]:
                    setattr(existing_user, field, getattr(user, field))
                existing_user.set_password(self.cleaned_data["password1"])
                try:
                    existing_user.save()
                    return existing_user, created
                except IntegrityError:
                    # Handle possible race condition
                    existing_user = CustomUser.objects.get(email=user.email)
                    return existing_user, False

            return existing_user, created

        return user, False


class ProfileSecurityForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Current Password"}),
        label="Current Password",
        required=False,
        max_length=100,
        min_length=8,
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "New Password"}),
        label="New Password",
        required=True,
        max_length=100,
        min_length=8,
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm New Password"}),
        label="Confirm New Password",
        required=True,
        max_length=100,
        min_length=8,
    )


class TokenDescriptionForm(forms.Form):
    token_desc = forms.CharField(max_length=255)


class SetNewPasswordForm(forms.Form):
    password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput,
        min_length=8
    )
    password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput,
        min_length=8
    )
