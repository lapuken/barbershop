from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied

from apps.core.constants import Roles
from apps.core.services import get_accessible_shops


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    allowed_roles = set()

    def test_func(self):
        return self.request.user.role == Roles.PLATFORM_ADMIN or self.request.user.role in self.allowed_roles

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied


class ActiveShopRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != Roles.PLATFORM_ADMIN and request.active_shop is None:
            messages.error(request, "Select a shop first.")
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class ShopScopedQuerysetMixin(LoginRequiredMixin):
    shop_field_name = "shop"

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.role == Roles.PLATFORM_ADMIN:
            shop_id = self.request.GET.get("shop") or self.request.session.get("active_shop_id")
            if shop_id:
                return queryset.filter(**{f"{self.shop_field_name}_id": shop_id})
            return queryset
        accessible = get_accessible_shops(user)
        return queryset.filter(**{f"{self.shop_field_name}__in": accessible})
