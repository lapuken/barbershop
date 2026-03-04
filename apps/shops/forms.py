from django import forms

from apps.shops.models import Shop


class ShopForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = [
            "name",
            "branch_code",
            "address",
            "phone",
            "whatsapp_number",
            "telegram_handle",
            "currency",
            "timezone",
            "is_active",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not field.widget.attrs.get("class"):
                field.widget.attrs["class"] = "form-control"
        self.fields["is_active"].widget.attrs["class"] = "form-check-input"
