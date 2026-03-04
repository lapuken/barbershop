from rest_framework.response import Response
from rest_framework.views import APIView

from apps.reports.services import (
    commission_summary,
    daily_sales_summary,
    expense_summary,
    monthly_sales_summary,
    net_revenue_summary,
    top_barbers_summary,
    weekly_sales_summary,
)


class DailyReportView(APIView):
    def get(self, request):
        return Response(daily_sales_summary(request.user, getattr(request, "active_shop", None)))


class WeeklyReportView(APIView):
    def get(self, request):
        return Response(weekly_sales_summary(request.user, getattr(request, "active_shop", None)))


class MonthlyReportView(APIView):
    def get(self, request):
        return Response(monthly_sales_summary(request.user, getattr(request, "active_shop", None)))


class TopBarbersReportView(APIView):
    def get(self, request):
        return Response(top_barbers_summary(request.user, getattr(request, "active_shop", None)))


class CommissionReportView(APIView):
    def get(self, request):
        return Response(commission_summary(request.user, getattr(request, "active_shop", None)))


class ExpenseReportView(APIView):
    def get(self, request):
        return Response(expense_summary(request.user, getattr(request, "active_shop", None)))


class NetRevenueReportView(APIView):
    def get(self, request):
        return Response(net_revenue_summary(request.user, getattr(request, "active_shop", None)))
