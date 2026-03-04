from __future__ import annotations

from django.db import models

from apps.core.models import TimeStampedModel


class Shop(TimeStampedModel):
    name = models.CharField(max_length=255)
    branch_code = models.CharField(max_length=32, unique=True)
    address = models.TextField()
    phone = models.CharField(max_length=32)
    whatsapp_number = models.CharField(max_length=32, blank=True)
    telegram_handle = models.CharField(max_length=64, blank=True)
    currency = models.CharField(max_length=8, default="USD")
    timezone = models.CharField(max_length=64, default="UTC")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["branch_code", "is_active"]),
            models.Index(fields=["is_active", "name"]),
        ]

    def __str__(self):
        return self.name
