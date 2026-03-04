from __future__ import annotations

from django.conf import settings
from django.db import models


class AuditLogQuerySet(models.QuerySet):
    def visible_to_user(self, user):
        if not user.is_authenticated:
            return self.none()
        if user.role == "platform_admin":
            return self
        return self.filter(models.Q(shop__user_accesses__user=user) | models.Q(shop__isnull=True)).distinct()


class AuditLog(models.Model):
    shop = models.ForeignKey("shops.Shop", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    event_type = models.CharField(max_length=64)
    entity_type = models.CharField(max_length=128)
    entity_id = models.CharField(max_length=64)
    old_values_json = models.JSONField(null=True, blank=True)
    new_values_json = models.JSONField(null=True, blank=True)
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["shop", "created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["event_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} {self.entity_type} {self.entity_id}"


class SecurityEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="security_events")
    event_type = models.CharField(max_length=64)
    identifier = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
        ]

    def __str__(self):
        return self.event_type
