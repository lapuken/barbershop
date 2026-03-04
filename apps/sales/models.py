from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.core.models import ShopScopedModel, SoftDeleteModel, TimeStampedModel


class Sale(ShopScopedModel, SoftDeleteModel):
    barber = models.ForeignKey("barbers.Barber", on_delete=models.PROTECT, related_name="sales")
    sale_date = models.DateField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="sales_created")
    updated_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="sales_updated")

    class Meta:
        ordering = ["-sale_date", "barber__full_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "barber", "sale_date"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_sale_per_barber_shop_day_active",
            )
        ]
        indexes = [
            models.Index(fields=["shop", "sale_date"]),
            models.Index(fields=["shop", "barber", "sale_date"]),
        ]

    def clean(self):
        if self.barber.shop_id != self.shop_id:
            raise ValidationError({"barber": "Barber must belong to the selected shop."})
        if not self.barber.is_active or self.barber.deleted_at is not None:
            raise ValidationError({"barber": "Inactive barber cannot receive new sales."})

    def __str__(self):
        return f"{self.shop.name} {self.barber.full_name} {self.sale_date}"


class SaleItem(TimeStampedModel):
    PRODUCT = "product"
    SERVICE = "service"
    ITEM_TYPE_CHOICES = [
        (PRODUCT, "Product"),
        (SERVICE, "Service"),
    ]

    sale = models.ForeignKey("sales.Sale", on_delete=models.CASCADE, related_name="items")
    item_type = models.CharField(max_length=16, choices=ITEM_TYPE_CHOICES)
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, null=True, blank=True, related_name="sale_items")
    item_name_snapshot = models.CharField(max_length=255)
    unit_price_snapshot = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["id"]

    def clean(self):
        if self.item_type == self.PRODUCT and not self.product:
            raise ValidationError({"product": "Product is required for product sale items."})
        if self.product and (not self.product.is_active or self.product.deleted_at is not None):
            raise ValidationError({"product": "Inactive product cannot be used in new sales."})
        if self.quantity < 1:
            raise ValidationError({"quantity": "Quantity must be at least 1."})

    def save(self, *args, **kwargs):
        self.line_total = Decimal(self.quantity) * self.unit_price_snapshot
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_name_snapshot} x {self.quantity}"
