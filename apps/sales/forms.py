from __future__ import annotations

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from apps.barbers.models import Barber
from apps.core.constants import Roles
from apps.core.services import get_shop_queryset_for_user
from apps.products.models import Product
from apps.sales.models import Sale, SaleItem


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ["shop", "barber", "sale_date", "notes"]
        widgets = {
            "sale_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, user=None, active_shop=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shop"].queryset = get_shop_queryset_for_user(user)
        shop_id = self.data.get("shop") if self.data else None
        shop = self.initial.get("shop") or getattr(self.instance, "shop", None) or active_shop
        if shop_id:
            shop = self.fields["shop"].queryset.filter(pk=shop_id).first() or shop
        self.fields["barber"].queryset = Barber.objects.filter(shop=shop, is_active=True) if shop else Barber.objects.none()
        if user and user.role != Roles.PLATFORM_ADMIN and active_shop:
            self.fields["shop"].initial = active_shop
            self.fields["shop"].widget = forms.HiddenInput()
        for name, field in self.fields.items():
            if not field.widget.attrs.get("class"):
                field.widget.attrs["class"] = "form-control"


class SaleItemForm(forms.ModelForm):
    class Meta:
        model = SaleItem
        fields = ["item_type", "product", "item_name_snapshot", "unit_price_snapshot", "quantity"]

    def __init__(self, *args, shop=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(shop=shop, is_active=True) if shop else Product.objects.none()
        self.fields["unit_price_snapshot"].widget.attrs["step"] = "0.01"
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        item_type = cleaned_data.get("item_type")
        product = cleaned_data.get("product")
        if item_type == SaleItem.PRODUCT:
            if not product:
                raise forms.ValidationError("Product is required for product items.")
            if not product.is_active or product.deleted_at is not None:
                raise forms.ValidationError("Inactive product cannot be used in new sales.")
        if item_type == SaleItem.SERVICE:
            if not cleaned_data.get("item_name_snapshot"):
                self.add_error("item_name_snapshot", "Service name is required.")
            if cleaned_data.get("unit_price_snapshot") is None:
                self.add_error("unit_price_snapshot", "Unit price is required.")
        return cleaned_data


class BaseSaleItemFormSet(BaseInlineFormSet):
    def __init__(self, *args, shop=None, **kwargs):
        self.shop = shop
        super().__init__(*args, **kwargs)
        for form in self.forms:
            form.fields["product"].queryset = Product.objects.filter(shop=shop, is_active=True) if shop else Product.objects.none()

    def clean(self):
        super().clean()
        has_items = False
        for form in self.forms:
            if not hasattr(form, "cleaned_data") or form.cleaned_data.get("DELETE"):
                continue
            if any(form.cleaned_data.values()):
                has_items = True
        if not has_items:
            raise forms.ValidationError("Add at least one sale item.")


SaleItemFormSet = inlineformset_factory(
    Sale,
    SaleItem,
    form=SaleItemForm,
    formset=BaseSaleItemFormSet,
    extra=1,
    can_delete=True,
)
