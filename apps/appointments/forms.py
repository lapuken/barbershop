from __future__ import annotations

from django import forms

from apps.appointments.models import Appointment, Customer
from apps.barbers.models import Barber
from apps.core.constants import Roles
from apps.core.services import get_shop_queryset_for_user
from apps.shops.models import Shop


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            "shop",
            "full_name",
            "phone",
            "email",
            "telegram_chat_id",
            "preferred_confirmation_channel",
            "notes",
            "is_active",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, user=None, active_shop=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shop"].queryset = get_shop_queryset_for_user(user)
        if user and user.role != Roles.PLATFORM_ADMIN and active_shop:
            self.fields["shop"].initial = active_shop
            self.fields["shop"].widget = forms.HiddenInput()
        self.fields["telegram_chat_id"].help_text = (
            "Required for automatic Telegram confirmations from the shop bot."
        )
        self.fields["preferred_confirmation_channel"].help_text = (
            "Automatic tries WhatsApp first, then Telegram when credentials and customer details exist."
        )
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif not field.widget.attrs.get("class"):
                field.widget.attrs["class"] = "form-control"


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = [
            "shop",
            "customer",
            "barber",
            "service_name",
            "scheduled_start",
            "duration_minutes",
            "expected_total",
            "status",
            "booking_source",
            "notes",
        ]
        widgets = {
            "scheduled_start": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, user=None, active_shop=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shop"].queryset = get_shop_queryset_for_user(user)
        shop_id = self.data.get("shop") if self.data else None
        shop = self.initial.get("shop") or getattr(self.instance, "shop", None) or active_shop
        if shop_id:
            shop = self.fields["shop"].queryset.filter(pk=shop_id).first() or shop
        self.fields["customer"].queryset = (
            Customer.objects.filter(shop=shop, is_active=True) if shop else Customer.objects.none()
        )
        self.fields["barber"].queryset = (
            Barber.objects.filter(shop=shop, is_active=True) if shop else Barber.objects.none()
        )
        self.fields["barber"].required = False
        if user and user.role != Roles.PLATFORM_ADMIN and active_shop:
            self.fields["shop"].initial = active_shop
            self.fields["shop"].widget = forms.HiddenInput()
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif not field.widget.attrs.get("class"):
                field.widget.attrs["class"] = "form-control"


class PublicBookingForm(forms.Form):
    shop = forms.ModelChoiceField(queryset=Shop.objects.filter(is_active=True))
    customer_name = forms.CharField(max_length=255)
    phone = forms.CharField(max_length=32, required=False)
    email = forms.EmailField(required=False)
    telegram_chat_id = forms.CharField(max_length=64, required=False)
    preferred_confirmation_channel = forms.ChoiceField(
        choices=Customer.ConfirmationChannel.choices,
        initial=Customer.ConfirmationChannel.AUTO,
    )
    barber = forms.ModelChoiceField(queryset=Barber.objects.none(), required=False)
    service_name = forms.CharField(max_length=255)
    scheduled_start = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )
    duration_minutes = forms.IntegerField(min_value=15, max_value=480, initial=45)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, selected_shop=None, **kwargs):
        super().__init__(*args, **kwargs)
        current_shop = selected_shop
        shop_id = self.data.get("shop") if self.data else None
        if shop_id:
            current_shop = Shop.objects.filter(pk=shop_id, is_active=True).first()
        elif self.initial.get("shop"):
            current_shop = self.initial["shop"]
        else:
            current_shop = self.fields["shop"].queryset.first()
            if current_shop:
                self.initial.setdefault("shop", current_shop)
        self.fields["barber"].queryset = (
            Barber.objects.filter(shop=current_shop, is_active=True)
            if current_shop
            else Barber.objects.none()
        )
        self.fields["telegram_chat_id"].help_text = (
            "Needed only if you want Telegram confirmations from the shop bot."
        )
        self.fields["preferred_confirmation_channel"].help_text = (
            "Choose where booking confirmations should be delivered."
        )
        for field in self.fields.values():
            if not field.widget.attrs.get("class"):
                field.widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        if (
            not cleaned_data.get("phone")
            and not cleaned_data.get("email")
            and not cleaned_data.get("telegram_chat_id")
        ):
            raise forms.ValidationError(
                (
                    "Provide at least a phone number, email address, or Telegram chat ID so "
                    "the shop can confirm your booking."
                )
            )
        preferred_channel = cleaned_data.get("preferred_confirmation_channel")
        if preferred_channel == Customer.ConfirmationChannel.WHATSAPP and not cleaned_data.get(
            "phone"
        ):
            self.add_error(
                "phone",
                "A phone number is required for WhatsApp confirmations.",
            )
        if preferred_channel == Customer.ConfirmationChannel.TELEGRAM and not cleaned_data.get(
            "telegram_chat_id"
        ):
            self.add_error(
                "telegram_chat_id",
                "A Telegram chat ID is required for Telegram confirmations.",
            )
        return cleaned_data
