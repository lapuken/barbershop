from django import forms

from apps.barbers.models import Barber
from apps.core.services import get_shop_queryset_for_user


class ReportFilterForm(forms.Form):
    shop = forms.ModelChoiceField(queryset=None, required=False)
    barber = forms.ModelChoiceField(queryset=Barber.objects.none(), required=False)
    category = forms.CharField(required=False)
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    active_status = forms.ChoiceField(choices=[("", "All"), ("active", "Active"), ("inactive", "Inactive")], required=False)

    def __init__(self, *args, user=None, active_shop=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shop"].queryset = get_shop_queryset_for_user(user)
        self.fields["barber"].queryset = Barber.objects.filter(shop=active_shop) if active_shop else Barber.objects.none()
        for name, field in self.fields.items():
            if not field.widget.attrs.get("class"):
                field.widget.attrs["class"] = "form-control"
