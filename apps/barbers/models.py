from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.core.models import ShopScopedModel, SoftDeleteModel


class Barber(ShopScopedModel, SoftDeleteModel):
    full_name = models.CharField(max_length=255)
    employee_code = models.CharField(max_length=64, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("50.00"))
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["shop__name", "full_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "full_name"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_barber_name_per_shop_active",
            ),
            models.UniqueConstraint(
                fields=["shop", "employee_code"],
                condition=Q(deleted_at__isnull=True) & ~Q(employee_code=""),
                name="uniq_barber_employee_per_shop_active",
            ),
            models.CheckConstraint(
                check=Q(commission_rate__gte=0) & Q(commission_rate__lte=100),
                name="barber_commission_between_0_100",
            ),
        ]
        indexes = [
            models.Index(fields=["shop", "is_active", "full_name"]),
        ]

    def clean(self):
        if not Decimal("0") <= self.commission_rate <= Decimal("100"):
            raise ValidationError({"commission_rate": "Commission rate must be between 0 and 100."})

    def __str__(self):
        return f"{self.full_name} ({self.shop.name})"
