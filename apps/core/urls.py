from django.urls import path

from apps.core import views

app_name = "core"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("healthz/", views.HealthCheckView.as_view(), name="healthz"),
    path("settings/", views.SettingsView.as_view(), name="settings"),
]
