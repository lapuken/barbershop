from django import forms

from apps.core.constants import Roles
from apps.core.services import get_shop_queryset_for_user
from apps.expenses.models import Expense


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["shop", "expense_date", "category", "description", "amount", "receipt"]
        widgets = {
            "expense_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, user=None, active_shop=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shop"].queryset = get_shop_queryset_for_user(user)
        if user and user.role != Roles.PLATFORM_ADMIN and active_shop:
            self.fields["shop"].initial = active_shop
            self.fields["shop"].widget = forms.HiddenInput()
        for name, field in self.fields.items():
            if not field.widget.attrs.get("class"):
                field.widget.attrs["class"] = "form-control"
