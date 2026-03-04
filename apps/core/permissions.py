from __future__ import annotations

from rest_framework.permissions import BasePermission

from apps.core.constants import Roles
from apps.core.services import user_can_access_shop


class ShopScopedPermission(BasePermission):
    allowed_roles = {role for role, _label in Roles.CHOICES}

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if user.role == Roles.PLATFORM_ADMIN:
            return True
        return user.role in self.allowed_roles

    def has_object_permission(self, request, view, obj):
        shop = getattr(obj, "shop", None)
        if shop is None and hasattr(obj, "sale"):
            shop = obj.sale.shop
        return shop is None or user_can_access_shop(request.user, shop)


class ManagementRolePermission(ShopScopedPermission):
    allowed_roles = Roles.MANAGEMENT


class SalesRolePermission(ShopScopedPermission):
    allowed_roles = Roles.SALES_ENTRY
