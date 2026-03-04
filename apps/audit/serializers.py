from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            "id",
            "shop",
            "actor",
            "event_type",
            "entity_type",
            "entity_id",
            "old_values_json",
            "new_values_json",
            "source_ip",
            "created_at",
        ]
