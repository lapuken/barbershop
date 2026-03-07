from django.contrib import admin

from apps.audit.models import AuditLog, SecurityEvent


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("event_type", "entity_type", "entity_id", "shop", "actor", "created_at")
    list_filter = ("event_type", "entity_type", "shop")
    search_fields = ("entity_id", "entity_type", "actor__username")
    readonly_fields = (
        "shop",
        "actor",
        "event_type",
        "entity_type",
        "entity_id",
        "old_values_json",
        "new_values_json",
        "source_ip",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "identifier", "ip_address", "created_at")
    list_filter = ("event_type",)
    readonly_fields = ("actor", "event_type", "identifier", "ip_address", "metadata", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
