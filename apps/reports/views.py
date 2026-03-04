from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.reports.forms import ReportFilterForm
from apps.reports.services import (
    build_dashboard_metrics,
    commission_summary,
    daily_sales_summary,
    expense_summary,
    monthly_sales_summary,
    net_revenue_summary,
    product_performance_summary,
    shop_comparison_summary,
    top_barbers_summary,
    weekly_sales_summary,
)


class ReportsDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "reports/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shop = self.request.active_shop
        context["filter_form"] = ReportFilterForm(self.request.GET or None, user=self.request.user, active_shop=shop)
        context["dashboard"] = build_dashboard_metrics(self.request.user, shop)
        context["daily"] = daily_sales_summary(self.request.user, shop)
        context["weekly"] = weekly_sales_summary(self.request.user, shop)
        context["monthly"] = monthly_sales_summary(self.request.user, shop)
        context["top_barbers"] = top_barbers_summary(self.request.user, shop)
        context["commissions"] = commission_summary(self.request.user, shop)
        context["expenses"] = expense_summary(self.request.user, shop)
        context["net_revenue"] = net_revenue_summary(self.request.user, shop)
        context["shop_comparison"] = shop_comparison_summary(self.request.user)
        context["product_performance"] = product_performance_summary(self.request.user, shop)
        return context
