from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, FormView, ListView, TemplateView, UpdateView, View

from apps.appointments.forms import AppointmentForm, CustomerForm, PublicBookingForm
from apps.appointments.models import Appointment, Customer
from apps.appointments.notifications import send_booking_confirmation
from apps.appointments.services import available_slots_for_shop, create_public_booking
from apps.appointments.sharing import (
    build_appointment_message,
    build_availability_message,
    build_shop_contact_message,
    build_telegram_direct_url,
    build_telegram_share_url,
    build_whatsapp_url,
)
from apps.core.constants import Roles
from apps.core.mixins import ActiveShopRequiredMixin, RoleRequiredMixin, ShopScopedQuerysetMixin
from apps.shops.models import Shop


class CustomerListView(ShopScopedQuerysetMixin, ActiveShopRequiredMixin, ListView):
    model = Customer
    paginate_by = 20
    template_name = "appointments/customer_list.html"
    context_object_name = "customers"

    def get_queryset(self):
        queryset = super().get_queryset().select_related("shop")
        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(full_name__icontains=search)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shop = self.request.active_shop
        share_links = {}
        if shop:
            availability = available_slots_for_shop(shop)
            availability_url = self.request.build_absolute_uri(
                f"{reverse('appointments:public-availability')}?shop={shop.id}"
            )
            share_text = build_availability_message(shop, availability, availability_url)
            for customer in context["customers"]:
                share_links[customer.id] = {
                    "whatsapp": build_whatsapp_url(customer.phone, share_text),
                    "telegram": build_telegram_share_url(share_text, availability_url),
                }
        context["customer_share_links"] = share_links
        return context


class CustomerCreateView(RoleRequiredMixin, ActiveShopRequiredMixin, CreateView):
    allowed_roles = Roles.SALES_ENTRY
    model = Customer
    form_class = CustomerForm
    template_name = "appointments/customer_form.html"
    success_url = reverse_lazy("appointments:customers")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["active_shop"] = self.request.active_shop
        return kwargs


class CustomerUpdateView(
    RoleRequiredMixin,
    ShopScopedQuerysetMixin,
    ActiveShopRequiredMixin,
    UpdateView,
):
    allowed_roles = Roles.SALES_ENTRY
    model = Customer
    form_class = CustomerForm
    template_name = "appointments/customer_form.html"
    success_url = reverse_lazy("appointments:customers")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["active_shop"] = self.request.active_shop
        return kwargs


class CustomerDeleteView(RoleRequiredMixin, ActiveShopRequiredMixin, View):
    allowed_roles = Roles.MANAGEMENT

    def post(self, request, pk):
        customer = get_object_or_404(Customer.all_objects.select_related("shop"), pk=pk)
        if request.user.role != Roles.PLATFORM_ADMIN and customer.shop != request.active_shop:
            return redirect("appointments:customers")
        customer.soft_delete(user=request.user)
        messages.success(request, "Customer archived.")
        return redirect("appointments:customers")


class AppointmentListView(ShopScopedQuerysetMixin, ActiveShopRequiredMixin, ListView):
    model = Appointment
    paginate_by = 25
    template_name = "appointments/appointment_list.html"
    context_object_name = "appointments"

    def get_queryset(self):
        queryset = super().get_queryset().select_related("shop", "customer", "barber")
        status = self.request.GET.get("status", "").strip()
        scheduled_date = self.request.GET.get("scheduled_date", "").strip()
        if status:
            queryset = queryset.filter(status=status)
        if scheduled_date:
            queryset = queryset.filter(scheduled_start__date=scheduled_date)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = Appointment.Status.choices
        share_links = {}
        shop = self.request.active_shop
        if shop:
            availability_url = self.request.build_absolute_uri(
                f"{reverse('appointments:public-availability')}?shop={shop.id}"
            )
            for appointment in context["appointments"]:
                message = build_appointment_message(appointment, availability_url)
                share_links[appointment.id] = {
                    "whatsapp": build_whatsapp_url(appointment.customer.phone, message),
                    "telegram": build_telegram_share_url(message, availability_url),
                }
        context["appointment_share_links"] = share_links
        return context


class AppointmentCreateView(RoleRequiredMixin, ActiveShopRequiredMixin, CreateView):
    allowed_roles = Roles.SALES_ENTRY
    model = Appointment
    form_class = AppointmentForm
    template_name = "appointments/appointment_form.html"
    success_url = reverse_lazy("appointments:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["active_shop"] = self.request.active_shop
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        if self.object.status == Appointment.Status.CONFIRMED:
            result = send_booking_confirmation(self.object, request=self.request)
            if result.sent:
                messages.success(
                    self.request,
                    f"Appointment saved. Confirmation sent via {result.channel_label}.",
                )
            elif result.status == "failed":
                messages.warning(
                    self.request,
                    "Appointment saved, but the booking confirmation could not be delivered.",
                )
            else:
                messages.success(self.request, "Appointment saved.")
                messages.warning(
                    self.request,
                    "Appointment saved, but no configured confirmation route was available.",
                )
        else:
            messages.success(self.request, "Appointment saved.")
        return response


class AppointmentUpdateView(
    RoleRequiredMixin,
    ShopScopedQuerysetMixin,
    ActiveShopRequiredMixin,
    UpdateView,
):
    allowed_roles = Roles.SALES_ENTRY
    model = Appointment
    form_class = AppointmentForm
    template_name = "appointments/appointment_form.html"
    success_url = reverse_lazy("appointments:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["active_shop"] = self.request.active_shop
        return kwargs

    def form_valid(self, form):
        previous_status = self.object.status
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        if previous_status != Appointment.Status.CONFIRMED and self.object.status == Appointment.Status.CONFIRMED:
            result = send_booking_confirmation(self.object, request=self.request)
            if result.sent:
                messages.success(
                    self.request,
                    f"Appointment updated. Confirmation sent via {result.channel_label}.",
                )
            elif result.status == "failed":
                messages.warning(
                    self.request,
                    "Appointment updated, but the booking confirmation could not be delivered.",
                )
            else:
                messages.success(self.request, "Appointment updated.")
                messages.warning(
                    self.request,
                    "Appointment updated, but no configured confirmation route was available.",
                )
        else:
            messages.success(self.request, "Appointment updated.")
        return response


class AppointmentDeleteView(RoleRequiredMixin, ActiveShopRequiredMixin, View):
    allowed_roles = Roles.MANAGEMENT

    def post(self, request, pk):
        appointment = get_object_or_404(Appointment.all_objects.select_related("shop"), pk=pk)
        if request.user.role != Roles.PLATFORM_ADMIN and appointment.shop != request.active_shop:
            return redirect("appointments:list")
        appointment.soft_delete(user=request.user)
        messages.success(request, "Appointment archived.")
        return redirect("appointments:list")


class PublicBookingView(FormView):
    template_name = "appointments/public_booking.html"
    form_class = PublicBookingForm
    success_url = reverse_lazy("appointments:public-success")

    def get_selected_shop(self):
        source = self.request.POST if self.request.method == "POST" else self.request.GET
        shop_id = source.get("shop", "").strip()
        if not shop_id:
            return Shop.objects.filter(is_active=True).order_by("name").first()
        return Shop.objects.filter(pk=shop_id, is_active=True).first()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        selected_shop = self.get_selected_shop()
        kwargs["selected_shop"] = selected_shop
        if selected_shop:
            kwargs.setdefault("initial", {})
            kwargs["initial"]["shop"] = selected_shop
        return kwargs

    def form_valid(self, form):
        create_public_booking(
            shop=form.cleaned_data["shop"],
            customer_name=form.cleaned_data["customer_name"],
            phone=form.cleaned_data.get("phone", ""),
            email=form.cleaned_data.get("email", ""),
            telegram_chat_id=form.cleaned_data.get("telegram_chat_id", ""),
            preferred_confirmation_channel=form.cleaned_data.get(
                "preferred_confirmation_channel"
            ),
            barber=form.cleaned_data.get("barber"),
            service_name=form.cleaned_data["service_name"],
            scheduled_start=form.cleaned_data["scheduled_start"],
            duration_minutes=form.cleaned_data["duration_minutes"],
            notes=form.cleaned_data.get("notes", ""),
        )
        messages.success(self.request, "Booking request submitted. The shop can now confirm it.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_shop = self.get_selected_shop()
        context["selected_shop"] = selected_shop
        if selected_shop:
            booking_url = self.request.build_absolute_uri(
                f"{reverse('appointments:public-book')}?shop={selected_shop.id}"
            )
            availability_url = self.request.build_absolute_uri(
                f"{reverse('appointments:public-availability')}?shop={selected_shop.id}"
            )
            contact_message = build_shop_contact_message(
                selected_shop,
                booking_url,
                availability_url,
            )
            context["shop_whatsapp_url"] = build_whatsapp_url(
                selected_shop.whatsapp_number,
                contact_message,
            )
            context["shop_telegram_url"] = build_telegram_direct_url(
                selected_shop.telegram_handle,
                contact_message,
            )
            context["availability_url"] = availability_url
        return context


class PublicBookingSuccessView(TemplateView):
    template_name = "appointments/public_booking_success.html"


class PublicAvailabilityView(TemplateView):
    template_name = "appointments/public_availability.html"

    def get_selected_shop(self):
        source = self.request.POST if self.request.method == "POST" else self.request.GET
        shop_id = source.get("shop", "").strip()
        if not shop_id:
            return Shop.objects.filter(is_active=True).order_by("name").first()
        return Shop.objects.filter(pk=shop_id, is_active=True).first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_shop = self.get_selected_shop()
        context["shops"] = Shop.objects.filter(is_active=True).order_by("name")
        context["selected_shop"] = selected_shop
        context["availability_groups"] = (
            available_slots_for_shop(selected_shop) if selected_shop else []
        )
        if selected_shop:
            booking_url = self.request.build_absolute_uri(
                f"{reverse('appointments:public-book')}?shop={selected_shop.id}"
            )
            availability_url = self.request.build_absolute_uri()
            share_text = build_availability_message(
                selected_shop,
                context["availability_groups"],
                availability_url,
            )
            contact_message = build_shop_contact_message(
                selected_shop,
                booking_url,
                availability_url,
            )
            context["booking_url"] = booking_url
            context["availability_whatsapp_share_url"] = build_whatsapp_url(
                selected_shop.whatsapp_number,
                share_text,
            )
            context["availability_telegram_share_url"] = build_telegram_share_url(
                share_text,
                availability_url,
            )
            context["shop_whatsapp_url"] = build_whatsapp_url(
                selected_shop.whatsapp_number,
                contact_message,
            )
            context["shop_telegram_url"] = build_telegram_direct_url(
                selected_shop.telegram_handle,
                contact_message,
            )
        return context
