from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.core.models import ShopScopedModel, SoftDeleteModel


class Product(ShopScopedModel, SoftDeleteModel):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=64)
    category = models.CharField(max_length=128)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    sale_price = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["shop__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "sku"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_product_sku_per_shop_active",
            ),
        ]
        indexes = [
            models.Index(fields=["shop", "is_active", "category"]),
            models.Index(fields=["shop", "sku"]),
        ]

    def clean(self):
        if self.sale_price < 0 or self.cost_price < 0:
            raise ValidationError("Product prices must be non-negative.")

    def __str__(self):
        return f"{self.name} ({self.shop.name})"
