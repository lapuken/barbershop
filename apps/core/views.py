from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.db import connections
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView

from apps.appointments.services import dashboard_appointment_metrics, upcoming_appointments_for_user
from apps.audit.models import AuditLog
from apps.reports.services import build_dashboard_metrics


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard"] = build_dashboard_metrics(self.request.user, self.request.active_shop)
        context["appointment_metrics"] = dashboard_appointment_metrics(
            self.request.user,
            self.request.active_shop,
        )
        context["upcoming_appointments"] = upcoming_appointments_for_user(
            self.request.user,
            self.request.active_shop,
        )
        context["recent_activity"] = AuditLog.objects.visible_to_user(self.request.user)[:10]
        return context


class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = "settings/settings.html"


class HealthCheckView(View):
    def get(self, request):
        database_ok = True
        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            database_ok = False

        status_code = 200 if database_ok else 503
        return JsonResponse(
            {
                "status": "ok" if database_ok else "degraded",
                "database": "up" if database_ok else "down",
                "release": settings.APP_RELEASE_SHA,
            },
            status=status_code,
        )
