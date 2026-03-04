from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.appointments.api import (
    AppointmentViewSet,
    CustomerViewSet,
    PublicAvailabilityAPIView,
    PublicBookingAPIView,
)
from apps.audit.api import AuditLogViewSet
from apps.barbers.api import BarberViewSet
from apps.core.api import DashboardReportView, LoginAPIView, LogoutAPIView
from apps.expenses.api import ExpenseViewSet
from apps.products.api import ProductViewSet
from apps.reports.api import (
    CommissionReportView,
    DailyReportView,
    ExpenseReportView,
    MonthlyReportView,
    NetRevenueReportView,
    TopBarbersReportView,
    WeeklyReportView,
)
from apps.sales.api import SaleViewSet
from apps.shops.api import ShopViewSet

router = DefaultRouter()
router.register("shops", ShopViewSet, basename="shop")
router.register("barbers", BarberViewSet, basename="barber")
router.register("products", ProductViewSet, basename="product")
router.register("sales", SaleViewSet, basename="sale")
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("customers", CustomerViewSet, basename="customer")
router.register("appointments", AppointmentViewSet, basename="appointment")
router.register("audit", AuditLogViewSet, basename="audit")

urlpatterns = [
    path("auth/login", LoginAPIView.as_view(), name="api-login"),
    path("auth/logout", LogoutAPIView.as_view(), name="api-logout"),
    path(
        "public/availability",
        PublicAvailabilityAPIView.as_view(),
        name="api-public-availability",
    ),
    path("public/bookings", PublicBookingAPIView.as_view(), name="api-public-booking"),
    path("reports/dashboard", DashboardReportView.as_view(), name="api-report-dashboard"),
    path("reports/daily", DailyReportView.as_view(), name="api-report-daily"),
    path("reports/weekly", WeeklyReportView.as_view(), name="api-report-weekly"),
    path("reports/monthly", MonthlyReportView.as_view(), name="api-report-monthly"),
    path("reports/top-barbers", TopBarbersReportView.as_view(), name="api-report-top-barbers"),
    path("reports/commissions", CommissionReportView.as_view(), name="api-report-commissions"),
    path("reports/expenses", ExpenseReportView.as_view(), name="api-report-expenses"),
    path("reports/net-revenue", NetRevenueReportView.as_view(), name="api-report-net-revenue"),
    path("", include(router.urls)),
]
