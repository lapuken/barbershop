from __future__ import annotations

from django import forms

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


class ShopSelectorForm(forms.Form):
    shop = forms.ModelChoiceField(
        queryset=None, widget=forms.Select(attrs={"class": "form-select"})
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shop"].queryset = get_shop_queryset_for_user(user)
