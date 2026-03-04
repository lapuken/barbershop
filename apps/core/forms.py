from django import forms


class ShopSelectionForm(forms.Form):
    shop = forms.ChoiceField()
