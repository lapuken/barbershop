from django import forms

from apps.barbers.models import Barber
from apps.core.constants import Roles
from apps.core.services import get_shop_queryset_for_user


class BarberForm(forms.ModelForm):
    class Meta:
        model = Barber
        fields = ["shop", "full_name", "employee_code", "phone", "commission_rate", "is_active"]

    def __init__(self, *args, user=None, active_shop=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["shop"].queryset = get_shop_queryset_for_user(user)
        if user and user.role != Roles.PLATFORM_ADMIN and active_shop:
            self.fields["shop"].initial = active_shop
            self.fields["shop"].widget = forms.HiddenInput()
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"
