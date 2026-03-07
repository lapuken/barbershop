from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from apps.core.constants import Roles
from apps.core.mixins import ActiveShopRequiredMixin, RoleRequiredMixin, ShopScopedQuerysetMixin
from apps.sales.forms import SaleForm, SaleItemFormSet
from apps.sales.models import Sale
from apps.sales.services import duplicate_sale_for, save_sale_with_items


class SaleListView(ShopScopedQuerysetMixin, ActiveShopRequiredMixin, ListView):
    model = Sale
    paginate_by = 20
    template_name = "sales/sale_list.html"
    context_object_name = "sales"

    def get_queryset(self):
        queryset = super().get_queryset().select_related("shop", "barber", "created_by")
        sale_date = self.request.GET.get("sale_date", "").strip()
        if sale_date:
            queryset = queryset.filter(sale_date=sale_date)
        return queryset


class BaseSaleEditView(RoleRequiredMixin, ActiveShopRequiredMixin, View):
    allowed_roles = Roles.SALES_ENTRY
    template_name = "sales/sale_form.html"
    object = None

    def get_object(self):
        return self.object

    def get_sale(self):
        if self.object is not None:
            return self.object
        return Sale(
            created_by=self.request.user,
            updated_by=self.request.user,
            shop=self.request.active_shop,
        )

    def get_form(self, data=None):
        sale = self.get_sale()
        initial = {}
        if sale.shop_id:
            initial["shop"] = sale.shop
        form = SaleForm(
            data=data,
            instance=sale,
            initial=initial,
            user=self.request.user,
            active_shop=self.request.active_shop,
        )
        return form

    def get_formset(self, data=None):
        sale = self.get_sale()
        shop = sale.shop if sale.pk else self.request.active_shop
        return SaleItemFormSet(data=data, instance=sale, prefix="items", shop=shop)

    def render_form(self, form, formset):
        return render(
            self.request,
            self.template_name,
            {"form": form, "formset": formset, "sale": self.get_object()},
        )

    def get(self, request, *args, **kwargs):
        return self.render_form(self.get_form(), self.get_formset())

    def post(self, request, *args, **kwargs):
        form = self.get_form(data=request.POST)
        formset = self.get_formset(data=request.POST)
        if form.is_valid() and formset.is_valid():
            sale = form.save(commit=False)
            duplicate = duplicate_sale_for(
                sale.shop, sale.barber, sale.sale_date, exclude_sale_id=sale.pk
            )
            if duplicate:
                messages.info(
                    request,
                    "A sale already exists for that barber and date. Redirected to edit mode.",
                )
                return redirect("sales:edit", pk=duplicate.pk)
            save_sale_with_items(sale=sale, items_data=formset.cleaned_data, user=request.user)
            messages.success(request, "Sale saved.")
            return redirect("sales:list")
        return self.render_form(form, formset)


class SaleCreateView(BaseSaleEditView):
    pass


class SaleUpdateView(BaseSaleEditView):
    def get_queryset(self):
        queryset = Sale.objects.select_related("shop", "barber")
        if self.request.user.role == Roles.PLATFORM_ADMIN:
            return queryset
        return queryset.filter(shop=self.request.active_shop)

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(self.get_queryset(), pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)


class SaleDeleteView(RoleRequiredMixin, ActiveShopRequiredMixin, View):
    allowed_roles = Roles.MANAGEMENT

    def post(self, request, pk):
        sale = get_object_or_404(Sale.all_objects.select_related("shop"), pk=pk)
        if request.user.role != Roles.PLATFORM_ADMIN and sale.shop != request.active_shop:
            return redirect("sales:list")
        sale.soft_delete(user=request.user)
        messages.success(request, "Sale archived.")
        return redirect("sales:list")
