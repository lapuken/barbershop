from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView, View

from apps.core.constants import Roles
from apps.core.mixins import ActiveShopRequiredMixin, RoleRequiredMixin, ShopScopedQuerysetMixin
from apps.expenses.forms import ExpenseForm
from apps.expenses.models import Expense


class ExpenseListView(ShopScopedQuerysetMixin, ActiveShopRequiredMixin, ListView):
    model = Expense
    paginate_by = 20
    template_name = "expenses/expense_list.html"
    context_object_name = "expenses"

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.GET.get("category", "").strip()
        if category:
            queryset = queryset.filter(category__icontains=category)
        return queryset.select_related("shop", "created_by")


class ExpenseCreateView(RoleRequiredMixin, ActiveShopRequiredMixin, CreateView):
    allowed_roles = Roles.SALES_ENTRY
    model = Expense
    form_class = ExpenseForm
    template_name = "expenses/expense_form.html"
    success_url = reverse_lazy("expenses:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["active_shop"] = self.request.active_shop
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class ExpenseUpdateView(
    RoleRequiredMixin, ShopScopedQuerysetMixin, ActiveShopRequiredMixin, UpdateView
):
    allowed_roles = Roles.SALES_ENTRY
    model = Expense
    form_class = ExpenseForm
    template_name = "expenses/expense_form.html"
    success_url = reverse_lazy("expenses:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["active_shop"] = self.request.active_shop
        return kwargs

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class ExpenseDeleteView(RoleRequiredMixin, ActiveShopRequiredMixin, View):
    allowed_roles = Roles.MANAGEMENT

    def post(self, request, pk):
        expense = get_object_or_404(Expense.all_objects.select_related("shop"), pk=pk)
        if request.user.role != Roles.PLATFORM_ADMIN and expense.shop != request.active_shop:
            return redirect("expenses:list")
        expense.soft_delete(user=request.user)
        messages.success(request, "Expense reversed.")
        return redirect("expenses:list")
