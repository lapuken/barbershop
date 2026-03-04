from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from apps.core.constants import Roles
from apps.core.mixins import RoleRequiredMixin
from apps.shops.forms import ShopForm
from apps.shops.models import Shop


class ShopListView(RoleRequiredMixin, ListView):
    allowed_roles = {Roles.PLATFORM_ADMIN}
    model = Shop
    template_name = "shops/shop_list.html"
    context_object_name = "shops"


class ShopCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = {Roles.PLATFORM_ADMIN}
    model = Shop
    form_class = ShopForm
    template_name = "shops/shop_form.html"
    success_url = reverse_lazy("shops:list")


class ShopUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = {Roles.PLATFORM_ADMIN}
    model = Shop
    form_class = ShopForm
    template_name = "shops/shop_form.html"
    success_url = reverse_lazy("shops:list")
