from django import forms

from apps.core.constants import Roles
from apps.core.services import get_shop_queryset_for_user
from apps.products.models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["shop", "name", "sku", "category", "cost_price", "sale_price", "is_active"]

    def __init__(self, *args, user=None, active_shop=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shop"].queryset = get_shop_queryset_for_user(user)
        if user and user.role != Roles.PLATFORM_ADMIN and active_shop:
            self.fields["shop"].initial = active_shop
            self.fields["shop"].widget = forms.HiddenInput()
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"
