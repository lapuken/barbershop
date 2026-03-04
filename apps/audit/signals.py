from __future__ import annotations

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.appointments.models import Appointment, Customer
from apps.audit.services import log_audit_event, snapshot_instance
from apps.barbers.models import Barber
from apps.expenses.models import Expense
from apps.products.models import Product
from apps.sales.models import Sale
from apps.shops.models import Shop

AUDITED_MODELS = (Shop, Barber, Product, Sale, Expense, Customer, Appointment)


@receiver(pre_save)
def capture_old_state(sender, instance, **kwargs):
    if sender not in AUDITED_MODELS or not instance.pk:
        return
    try:
        old_instance = sender.all_objects.get(pk=instance.pk) if hasattr(sender, "all_objects") else sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    instance._audit_old_values = snapshot_instance(old_instance)


@receiver(post_save)
def write_audit_save(sender, instance, created, **kwargs):
    if sender not in AUDITED_MODELS:
        return
    old_values = getattr(instance, "_audit_old_values", None)
    new_values = snapshot_instance(instance)
    log_audit_event(instance, "create" if created else "update", old_values=old_values, new_values=new_values)


@receiver(post_delete)
def write_audit_delete(sender, instance, **kwargs):
    if sender not in AUDITED_MODELS:
        return
    log_audit_event(instance, "delete", old_values=snapshot_instance(instance), new_values=None)
