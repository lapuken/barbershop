from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView, View
from django.shortcuts import redirect, get_object_or_404

from apps.barbers.forms import BarberForm
from apps.barbers.models import Barber
from apps.core.constants import Roles
from apps.core.mixins import ActiveShopRequiredMixin, RoleRequiredMixin, ShopScopedQuerysetMixin


class BarberListView(ShopScopedQuerysetMixin, ActiveShopRequiredMixin, ListView):
    model = Barber
    paginate_by = 20
    template_name = "barbers/barber_list.html"
    context_object_name = "barbers"

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(full_name__icontains=search)
        return queryset.select_related("shop")


class BarberCreateView(RoleRequiredMixin, ActiveShopRequiredMixin, CreateView):
    allowed_roles = Roles.MANAGEMENT
    model = Barber
    form_class = BarberForm
    template_name = "barbers/barber_form.html"
    success_url = reverse_lazy("barbers:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["active_shop"] = self.request.active_shop
        return kwargs


class BarberUpdateView(RoleRequiredMixin, ShopScopedQuerysetMixin, ActiveShopRequiredMixin, UpdateView):
    allowed_roles = Roles.MANAGEMENT
    model = Barber
    form_class = BarberForm
    template_name = "barbers/barber_form.html"
    success_url = reverse_lazy("barbers:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["active_shop"] = self.request.active_shop
        return kwargs


class BarberDeleteView(RoleRequiredMixin, ShopScopedQuerysetMixin, ActiveShopRequiredMixin, View):
    allowed_roles = Roles.MANAGEMENT

    def post(self, request, pk):
        barber = get_object_or_404(Barber.all_objects.select_related("shop"), pk=pk)
        if request.user.role != Roles.PLATFORM_ADMIN and barber.shop != request.active_shop:
            return redirect("barbers:list")
        barber.soft_delete(user=request.user)
        messages.success(request, "Barber archived.")
        return redirect("barbers:list")
