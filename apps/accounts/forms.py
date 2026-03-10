from __future__ import annotations

from django import forms
from django.contrib.auth.forms import PasswordChangeForm

from apps.core.services import get_shop_queryset_for_user


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "username"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "current-password"}
        )
    )

    def __init__(self, *args, request=None, **kwargs):
        # LoginView passes request to the authentication form contract.
        super().__init__(*args, **kwargs)
        self.request = request


class AppPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field_attrs = {
            "old_password": {"autocomplete": "current-password"},
            "new_password1": {"autocomplete": "new-password"},
            "new_password2": {"autocomplete": "new-password"},
        }
        for field_name, attrs in field_attrs.items():
            self.fields[field_name].widget.attrs.update({"class": "form-control", **attrs})


class ShopSelectorForm(forms.Form):
    shop = forms.ModelChoiceField(
        queryset=None, widget=forms.Select(attrs={"class": "form-select"})
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shop"].queryset = get_shop_queryset_for_user(user)
