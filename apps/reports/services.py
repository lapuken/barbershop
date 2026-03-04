from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, F, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.core.constants import Roles
from apps.core.services import get_accessible_shops
from apps.expenses.models import Expense
from apps.sales.models import Sale, SaleItem


def _base_sales(user, shop=None):
    queryset = Sale.objects.filter(deleted_at__isnull=True).select_related("shop", "barber")
    if user.role == Roles.PLATFORM_ADMIN:
        return queryset.filter(shop=shop) if shop else queryset
    shops = get_accessible_shops(user)
    queryset = queryset.filter(shop__in=shops)
    return queryset.filter(shop=shop) if shop else queryset


def _base_expenses(user, shop=None):
    queryset = Expense.objects.filter(deleted_at__isnull=True).select_related("shop")
    if user.role == Roles.PLATFORM_ADMIN:
        return queryset.filter(shop=shop) if shop else queryset
    shops = get_accessible_shops(user)
    queryset = queryset.filter(shop__in=shops)
    return queryset.filter(shop=shop) if shop else queryset


def _totals_for_period(user, start_date: date, end_date: date, shop=None):
    sales = _base_sales(user, shop=shop).filter(sale_date__range=(start_date, end_date))
    expenses = _base_expenses(user, shop=shop).filter(expense_date__range=(start_date, end_date))
    total_sales = sales.aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))["total"]
    total_commissions = sales.aggregate(total=Coalesce(Sum("commission_amount"), Decimal("0.00")))["total"]
    total_expenses = expenses.aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]
    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_sales": total_sales,
        "total_commissions": total_commissions,
        "total_expenses": total_expenses,
        "net_revenue": total_sales - total_commissions - total_expenses,
    }


def build_dashboard_metrics(user, shop=None):
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    today_metrics = _totals_for_period(user, today, today, shop=shop)
    weekly_metrics = _totals_for_period(user, week_start, today, shop=shop)
    monthly_metrics = _totals_for_period(user, month_start, today, shop=shop)
    top_barber = (
        _base_sales(user, shop=shop)
        .filter(sale_date=today)
        .values(name=F("barber__full_name"))
        .annotate(revenue=Coalesce(Sum("total_amount"), Decimal("0.00")))
        .order_by("-revenue")
        .first()
    )
    return {
        "today": today_metrics,
        "weekly": weekly_metrics,
        "monthly": monthly_metrics,
        "top_barber": top_barber,
    }


def daily_sales_summary(user, shop=None, day=None):
    day = day or timezone.localdate()
    data = _totals_for_period(user, day, day, shop=shop)
    data["sales"] = list(
        _base_sales(user, shop=shop)
        .filter(sale_date=day)
        .values("id", "shop__name", "barber__full_name", "total_amount", "commission_amount", "sale_date")
        .order_by("barber__full_name")
    )
    return data


def weekly_sales_summary(user, shop=None, end_date=None):
    end_date = end_date or timezone.localdate()
    start_date = end_date - timedelta(days=end_date.weekday())
    data = _totals_for_period(user, start_date, end_date, shop=shop)
    data["daily_breakdown"] = list(
        _base_sales(user, shop=shop)
        .filter(sale_date__range=(start_date, end_date))
        .values("sale_date")
        .annotate(total_sales=Coalesce(Sum("total_amount"), Decimal("0.00")))
        .order_by("sale_date")
    )
    return data


def monthly_sales_summary(user, shop=None, day=None):
    day = day or timezone.localdate()
    start_date = day.replace(day=1)
    return _totals_for_period(user, start_date, day, shop=shop)


def top_barbers_summary(user, shop=None, start_date=None, end_date=None):
    if not start_date:
        start_date = timezone.localdate().replace(day=1)
    if not end_date:
        end_date = timezone.localdate()
    return list(
        _base_sales(user, shop=shop)
        .filter(sale_date__range=(start_date, end_date))
        .values("barber__id", "barber__full_name")
        .annotate(
            revenue=Coalesce(Sum("total_amount"), Decimal("0.00")),
            commissions=Coalesce(Sum("commission_amount"), Decimal("0.00")),
            sale_days=Count("id"),
        )
        .order_by("-revenue")
    )


def commission_summary(user, shop=None, start_date=None, end_date=None):
    if not start_date:
        start_date = timezone.localdate().replace(day=1)
    if not end_date:
        end_date = timezone.localdate()
    return {
        "start_date": start_date,
        "end_date": end_date,
        "results": top_barbers_summary(user, shop=shop, start_date=start_date, end_date=end_date),
    }


def expense_summary(user, shop=None, start_date=None, end_date=None):
    if not start_date:
        start_date = timezone.localdate().replace(day=1)
    if not end_date:
        end_date = timezone.localdate()
    results = list(
        _base_expenses(user, shop=shop)
        .filter(expense_date__range=(start_date, end_date))
        .values("category")
        .annotate(total=Coalesce(Sum("amount"), Decimal("0.00")))
        .order_by("-total")
    )
    return {"start_date": start_date, "end_date": end_date, "results": results}


def net_revenue_summary(user, shop=None, start_date=None, end_date=None):
    if not start_date:
        start_date = timezone.localdate().replace(day=1)
    if not end_date:
        end_date = timezone.localdate()
    return _totals_for_period(user, start_date, end_date, shop=shop)


def shop_comparison_summary(user, start_date=None, end_date=None):
    if not start_date:
        start_date = timezone.localdate().replace(day=1)
    if not end_date:
        end_date = timezone.localdate()
    queryset = _base_sales(user).filter(sale_date__range=(start_date, end_date))
    return list(
        queryset.values("shop__id", "shop__name")
        .annotate(
            total_sales=Coalesce(Sum("total_amount"), Decimal("0.00")),
            total_commissions=Coalesce(Sum("commission_amount"), Decimal("0.00")),
        )
        .order_by("-total_sales")
    )


def product_performance_summary(user, shop=None, start_date=None, end_date=None):
    if not start_date:
        start_date = timezone.localdate().replace(day=1)
    if not end_date:
        end_date = timezone.localdate()
    sale_items = SaleItem.objects.filter(sale__deleted_at__isnull=True, sale__sale_date__range=(start_date, end_date))
    if user.role != Roles.PLATFORM_ADMIN:
        sale_items = sale_items.filter(sale__shop__in=get_accessible_shops(user))
    if shop:
        sale_items = sale_items.filter(sale__shop=shop)
    return list(
        sale_items.values("item_name_snapshot")
        .annotate(quantity_sold=Coalesce(Sum("quantity"), 0), revenue=Coalesce(Sum("line_total"), Decimal("0.00")))
        .order_by("-revenue")
    )
