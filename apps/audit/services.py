from __future__ import annotations

import json
from decimal import Decimal

from django.forms.models import model_to_dict

from apps.audit.middleware import get_current_request
from apps.audit.models import AuditLog, SecurityEvent


def _normalize_value(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "pk"):
        return value.pk
    if isinstance(value, dict):
        return {key: _normalize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_normalize_value(item) for item in value]
    if hasattr(value, "name") and not isinstance(value, str):
        return getattr(value, "name", "") or ""
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def _normalize_payload(payload):
    if payload is None:
        return None
    return {key: _normalize_value(value) for key, value in payload.items()}


def log_audit_event(instance, event_type: str, old_values=None, new_values=None):
    request = get_current_request()
    actor = getattr(request, "user", None)
    source_ip = request.META.get("REMOTE_ADDR") if request else None
    shop = getattr(instance, "shop", None)
    AuditLog.objects.create(
        shop=shop,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        event_type=event_type,
        entity_type=instance.__class__.__name__,
        entity_id=str(instance.pk),
        old_values_json=_normalize_payload(old_values),
        new_values_json=_normalize_payload(new_values),
        source_ip=source_ip,
    )


def snapshot_instance(instance):
    fields = [field.name for field in instance._meta.fields]
    return model_to_dict(instance, fields=fields)


def log_security_event(event_type: str, actor=None, identifier="", ip_address="", metadata=None):
    SecurityEvent.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else actor,
        event_type=event_type,
        identifier=identifier,
        ip_address=ip_address or None,
        metadata=metadata or {},
    )
