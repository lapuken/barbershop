from django.urls import path

from apps.reports.views import ReportsDashboardView

app_name = "reports"

urlpatterns = [
    path("", ReportsDashboardView.as_view(), name="dashboard"),
]
