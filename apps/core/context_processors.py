from __future__ import annotations

import time

from django.conf import settings

from apps.core.constants import Roles
from apps.core.services import get_accessible_shops


def current_shop(request):
    if not request.user.is_authenticated:
        return {
            "current_shop": None,
            "accessible_shops": [],
            "can_access_shop_scoped_nav": False,
            "can_manage_shops": False,
            "can_edit_customers": False,
            "can_archive_customers": False,
            "can_edit_appointments": False,
            "can_archive_appointments": False,
            "can_manage_barbers": False,
            "can_manage_products": False,
            "can_edit_sales": False,
            "can_archive_sales": False,
            "can_edit_expenses": False,
            "can_archive_expenses": False,
        }

    current_shop = getattr(request, "active_shop", None)
    role = request.user.role
    can_access_shop_scoped_nav = role == Roles.PLATFORM_ADMIN or current_shop is not None
    is_management = role in Roles.MANAGEMENT
    is_sales_entry = role in Roles.SALES_ENTRY

    return {
        "current_shop": current_shop,
        "accessible_shops": get_accessible_shops(request.user),
        "can_access_shop_scoped_nav": can_access_shop_scoped_nav,
        "can_manage_shops": role == Roles.PLATFORM_ADMIN,
        "can_edit_customers": can_access_shop_scoped_nav and is_sales_entry,
        "can_archive_customers": can_access_shop_scoped_nav and is_management,
        "can_edit_appointments": can_access_shop_scoped_nav and is_sales_entry,
        "can_archive_appointments": can_access_shop_scoped_nav and is_management,
        "can_manage_barbers": can_access_shop_scoped_nav and is_management,
        "can_manage_products": can_access_shop_scoped_nav and is_management,
        "can_edit_sales": can_access_shop_scoped_nav and is_sales_entry,
        "can_archive_sales": can_access_shop_scoped_nav and is_management,
        "can_edit_expenses": can_access_shop_scoped_nav and is_sales_entry,
        "can_archive_expenses": can_access_shop_scoped_nav and is_management,
    }


def asset_version(request):
    if settings.DEBUG:
        return {"asset_version": str(int(time.time()))}
    return {"asset_version": settings.APP_RELEASE_SHA}
