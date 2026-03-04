from __future__ import annotations


class Roles:
    PLATFORM_ADMIN = "platform_admin"
    SHOP_OWNER = "shop_owner"
    SHOP_MANAGER = "shop_manager"
    CASHIER = "cashier"
    BARBER = "barber"

    CHOICES = [
        (PLATFORM_ADMIN, "Platform Admin"),
        (SHOP_OWNER, "Shop Owner"),
        (SHOP_MANAGER, "Shop Manager"),
        (CASHIER, "Cashier / Front Desk"),
        (BARBER, "Barber"),
    ]

    MANAGEMENT = {PLATFORM_ADMIN, SHOP_OWNER, SHOP_MANAGER}
    SALES_ENTRY = {PLATFORM_ADMIN, SHOP_OWNER, SHOP_MANAGER, CASHIER}
    BARBER_ASSIGNMENT = MANAGEMENT | {CASHIER}
