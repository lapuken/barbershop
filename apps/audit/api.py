from rest_framework import mixins, viewsets

from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer


class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        return AuditLog.objects.visible_to_user(self.request.user).select_related("shop", "actor")
