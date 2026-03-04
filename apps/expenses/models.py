from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from apps.core.models import ShopScopedModel, SoftDeleteModel


class Expense(ShopScopedModel, SoftDeleteModel):
    expense_date = models.DateField()
    category = models.CharField(max_length=128)
    description = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    receipt = models.FileField(
        upload_to="receipts/",
        blank=True,
        validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png"])],
    )
    created_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="expenses_created")
    updated_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="expenses_updated")

    class Meta:
        ordering = ["-expense_date", "-created_at"]
        indexes = [
            models.Index(fields=["shop", "expense_date"]),
            models.Index(fields=["shop", "category"]),
        ]

    def clean(self):
        if self.amount <= Decimal("0.00"):
            raise ValidationError({"amount": "Amount must be positive."})

    def __str__(self):
        return f"{self.shop.name} {self.category} {self.expense_date}"
