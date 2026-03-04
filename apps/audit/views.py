from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from apps.audit.models import AuditLog


class AuditLogListView(LoginRequiredMixin, ListView):
    model = AuditLog
    paginate_by = 25
    template_name = "audit/audit_list.html"
    context_object_name = "audit_logs"

    def get_queryset(self):
        return AuditLog.objects.visible_to_user(self.request.user).select_related("shop", "actor")
