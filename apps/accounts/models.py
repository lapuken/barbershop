from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.constants import Roles
from apps.core.models import TimeStampedModel


class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields["role"] = Roles.PLATFORM_ADMIN
        return super().create_superuser(username, email=email, password=password, **extra_fields)


class User(AbstractUser):
    role = models.CharField(max_length=32, choices=Roles.CHOICES, default=Roles.CASHIER)
    phone = models.CharField(max_length=32, blank=True)
    must_change_password = models.BooleanField(default=False)
    objects = UserManager()

    class Meta:
        ordering = ["username"]


class UserShopAccess(TimeStampedModel):
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="shop_accesses"
    )
    shop = models.ForeignKey("shops.Shop", on_delete=models.CASCADE, related_name="user_accesses")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "shop")
        verbose_name = "User Shop Access"
        verbose_name_plural = "User Shop Access"
        indexes = [
            models.Index(fields=["user", "shop", "is_active"]),
        ]

    def clean(self):
        if self.user.role == Roles.PLATFORM_ADMIN:
            raise ValidationError("Platform admins do not need shop access assignments.")

    def __str__(self):
        return f"{self.user.username} -> {self.shop.name}"
