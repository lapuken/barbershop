from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView, View

from apps.core.constants import Roles
from apps.core.mixins import ActiveShopRequiredMixin, RoleRequiredMixin, ShopScopedQuerysetMixin
from apps.products.forms import ProductForm
from apps.products.models import Product


class ProductListView(ShopScopedQuerysetMixin, ActiveShopRequiredMixin, ListView):
    model = Product
    paginate_by = 20
    template_name = "products/product_list.html"
    context_object_name = "products"

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset.select_related("shop")


class ProductCreateView(RoleRequiredMixin, ActiveShopRequiredMixin, CreateView):
    allowed_roles = Roles.MANAGEMENT
    model = Product
    form_class = ProductForm
    template_name = "products/product_form.html"
    success_url = reverse_lazy("products:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["active_shop"] = self.request.active_shop
        return kwargs


class ProductUpdateView(
    RoleRequiredMixin, ShopScopedQuerysetMixin, ActiveShopRequiredMixin, UpdateView
):
    allowed_roles = Roles.MANAGEMENT
    model = Product
    form_class = ProductForm
    template_name = "products/product_form.html"
    success_url = reverse_lazy("products:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["active_shop"] = self.request.active_shop
        return kwargs


class ProductDeleteView(RoleRequiredMixin, ActiveShopRequiredMixin, View):
    allowed_roles = Roles.MANAGEMENT

    def post(self, request, pk):
        product = get_object_or_404(Product.all_objects.select_related("shop"), pk=pk)
        if request.user.role != Roles.PLATFORM_ADMIN and product.shop != request.active_shop:
            return redirect("products:list")
        product.soft_delete(user=request.user)
        messages.success(request, "Product archived.")
        return redirect("products:list")
