from __future__ import annotations

import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import UserShopAccess
from apps.barbers.models import Barber
from apps.core.constants import Roles
from apps.products.models import Product
from apps.shops.models import Shop


class Command(BaseCommand):
    help = "Initialize go-live application data from a JSON configuration file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--config",
            required=True,
            help="Path to a JSON file describing the go-live data to create or update.",
        )
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Reset passwords for existing users to the values in the config file.",
        )

    def handle(self, *args, **options):
        config = self._load_config(options["config"])
        reset_passwords = options["reset_passwords"]
        self.summary = Counter()

        with transaction.atomic():
            self._sync_platform_admin(config.get("platform_admin"), reset_passwords)

            shops_data = config.get("shops")
            if not isinstance(shops_data, list) or not shops_data:
                raise CommandError("Config must include a non-empty 'shops' list.")

            for shop_data in shops_data:
                self._sync_shop(shop_data, reset_passwords)

        self.stdout.write(self.style.SUCCESS("Go-live data initialization complete."))
        self.stdout.write(
            "Created:"
            f" shops={self.summary['shops_created']},"
            f" users={self.summary['users_created']},"
            f" shop_accesses={self.summary['shop_accesses_created']},"
            f" barbers={self.summary['barbers_created']},"
            f" products={self.summary['products_created']}"
        )
        self.stdout.write(
            "Updated:"
            f" shops={self.summary['shops_updated']},"
            f" users={self.summary['users_updated']},"
            f" shop_accesses={self.summary['shop_accesses_updated']},"
            f" barbers={self.summary['barbers_updated']},"
            f" products={self.summary['products_updated']}"
        )

    def _load_config(self, config_path: str) -> dict:
        path = Path(config_path).expanduser()
        if not path.is_file():
            raise CommandError(f"Config file not found: {path}")

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"Config file is not valid JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise CommandError("Top-level JSON value must be an object.")
        return data

    def _sync_platform_admin(self, admin_data: dict | None, reset_passwords: bool) -> None:
        User = get_user_model()

        if admin_data is None:
            if User.objects.filter(role=Roles.PLATFORM_ADMIN, is_active=True).exists():
                return
            raise CommandError(
                "Config must include 'platform_admin' when no active platform admin exists."
            )

        if not isinstance(admin_data, dict):
            raise CommandError("'platform_admin' must be an object.")

        self._sync_user(
            admin_data,
            reset_passwords=reset_passwords,
            allow_platform_admin=True,
        )

    def _sync_shop(self, shop_data: dict, reset_passwords: bool) -> None:
        if not isinstance(shop_data, dict):
            raise CommandError("Each item in 'shops' must be an object.")

        branch_code = self._required_string(shop_data, "branch_code")
        defaults = {
            "name": self._required_string(shop_data, "name"),
            "address": self._required_string(shop_data, "address"),
            "phone": self._required_string(shop_data, "phone"),
            "whatsapp_number": self._string(shop_data, "whatsapp_number", ""),
            "telegram_handle": self._string(shop_data, "telegram_handle", ""),
            "currency": self._string(shop_data, "currency", "USD"),
            "timezone": self._string(shop_data, "timezone", "UTC"),
            "is_active": self._bool(shop_data, "is_active", True),
        }

        shop, created = Shop.objects.update_or_create(branch_code=branch_code, defaults=defaults)
        self.summary["shops_created" if created else "shops_updated"] += 1

        users_data = shop_data.get("users", [])
        if users_data and not isinstance(users_data, list):
            raise CommandError(f"Shop '{branch_code}' has a non-list 'users' value.")
        for user_data in users_data:
            user = self._sync_user(user_data, reset_passwords=reset_passwords)
            access, access_created = UserShopAccess.objects.update_or_create(
                user=user,
                shop=shop,
                defaults={"is_active": self._bool(user_data, "shop_access_is_active", True)},
            )
            access.full_clean()
            access.save()
            self.summary[
                "shop_accesses_created" if access_created else "shop_accesses_updated"
            ] += 1

        barbers_data = shop_data.get("barbers", [])
        if barbers_data and not isinstance(barbers_data, list):
            raise CommandError(f"Shop '{branch_code}' has a non-list 'barbers' value.")
        for barber_data in barbers_data:
            self._sync_barber(shop, barber_data)

        products_data = shop_data.get("products", [])
        if products_data and not isinstance(products_data, list):
            raise CommandError(f"Shop '{branch_code}' has a non-list 'products' value.")
        for product_data in products_data:
            self._sync_product(shop, product_data)

        self._validate_shop_readiness(shop)

    def _sync_user(
        self,
        user_data: dict,
        *,
        reset_passwords: bool,
        allow_platform_admin: bool = False,
    ):
        if not isinstance(user_data, dict):
            raise CommandError("Each user entry must be an object.")

        User = get_user_model()
        username = self._required_string(user_data, "username")
        role = self._required_role(user_data, allow_platform_admin=allow_platform_admin)
        password = self._required_string(user_data, "password")

        user, created = User.objects.get_or_create(username=username)
        user.email = self._required_string(user_data, "email")
        user.role = role
        user.phone = self._string(user_data, "phone", "")
        user.must_change_password = self._bool(user_data, "must_change_password", False)
        user.is_active = self._bool(user_data, "is_active", True)
        user.is_staff = role in Roles.MANAGEMENT
        user.is_superuser = role == Roles.PLATFORM_ADMIN

        if created or reset_passwords or not user.has_usable_password():
            user.set_password(password)

        user.full_clean()
        user.save()
        self.summary["users_created" if created else "users_updated"] += 1
        return user

    def _sync_barber(self, shop: Shop, barber_data: dict) -> None:
        if not isinstance(barber_data, dict):
            raise CommandError(f"Shop '{shop.branch_code}' has a non-object barber entry.")

        barber = self._find_barber(shop, barber_data)
        created = barber is None
        if barber is None:
            barber = Barber(shop=shop)

        barber.full_name = self._required_string(barber_data, "full_name")
        barber.employee_code = self._string(barber_data, "employee_code", "")
        barber.phone = self._string(barber_data, "phone", "")
        barber.commission_rate = self._decimal(barber_data, "commission_rate", Decimal("50.00"))
        barber.is_active = self._bool(barber_data, "is_active", True)
        barber.deleted_at = None
        barber.deleted_by = None
        barber.full_clean()
        barber.save()
        self.summary["barbers_created" if created else "barbers_updated"] += 1

    def _sync_product(self, shop: Shop, product_data: dict) -> None:
        if not isinstance(product_data, dict):
            raise CommandError(f"Shop '{shop.branch_code}' has a non-object product entry.")

        sku = self._required_string(product_data, "sku")
        product = Product.all_objects.filter(shop=shop, sku=sku).first()
        created = product is None
        if product is None:
            product = Product(shop=shop, sku=sku)

        product.name = self._required_string(product_data, "name")
        product.category = self._required_string(product_data, "category")
        product.cost_price = self._decimal(product_data, "cost_price", Decimal("0.00"))
        product.sale_price = self._decimal(product_data, "sale_price")
        product.is_active = self._bool(product_data, "is_active", True)
        product.deleted_at = None
        product.deleted_by = None
        product.full_clean()
        product.save()
        self.summary["products_created" if created else "products_updated"] += 1

    def _find_barber(self, shop: Shop, barber_data: dict):
        employee_code = self._string(barber_data, "employee_code", "")
        if employee_code:
            barber = Barber.all_objects.filter(shop=shop, employee_code=employee_code).first()
            if barber is not None:
                return barber
        full_name = self._required_string(barber_data, "full_name")
        return Barber.all_objects.filter(shop=shop, full_name=full_name).first()

    def _validate_shop_readiness(self, shop: Shop) -> None:
        if not shop.is_active:
            return

        active_operator_exists = UserShopAccess.objects.filter(
            shop=shop,
            is_active=True,
            user__is_active=True,
            user__role__in={Roles.SHOP_OWNER, Roles.SHOP_MANAGER, Roles.CASHIER},
        ).exists()
        if not active_operator_exists:
            raise CommandError(
                f"Active shop '{shop.branch_code}' must have at least one active "
                "shop_owner, shop_manager, or cashier user."
            )

        active_barber_exists = Barber.objects.filter(shop=shop, is_active=True).exists()
        if not active_barber_exists:
            raise CommandError(
                f"Active shop '{shop.branch_code}' must have at least one active barber."
            )

    def _required_role(self, data: dict, *, allow_platform_admin: bool) -> str:
        if allow_platform_admin and "role" not in data:
            return Roles.PLATFORM_ADMIN

        role = self._required_string(data, "role")
        valid_roles = {value for value, _label in Roles.CHOICES}
        if role not in valid_roles:
            raise CommandError(
                f"Invalid role '{role}'. Expected one of: {', '.join(sorted(valid_roles))}."
            )
        if allow_platform_admin and role != Roles.PLATFORM_ADMIN:
            raise CommandError("The 'platform_admin' entry must use the 'platform_admin' role.")
        if role == Roles.PLATFORM_ADMIN and not allow_platform_admin:
            raise CommandError("Shop-level user entries cannot use the 'platform_admin' role.")
        return role

    def _required_string(self, data: dict, key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise CommandError(f"Field '{key}' is required and must be a non-empty string.")
        return value.strip()

    def _string(self, data: dict, key: str, default: str) -> str:
        value = data.get(key, default)
        if value is None:
            return default
        if not isinstance(value, str):
            raise CommandError(f"Field '{key}' must be a string.")
        return value.strip()

    def _bool(self, data: dict, key: str, default: bool) -> bool:
        value = data.get(key, default)
        if not isinstance(value, bool):
            raise CommandError(f"Field '{key}' must be a boolean.")
        return value

    def _decimal(self, data: dict, key: str, default: Decimal | None = None) -> Decimal:
        if key not in data:
            if default is None:
                raise CommandError(f"Field '{key}' is required.")
            return default

        value = data[key]
        if isinstance(value, int):
            value = str(value)
        if not isinstance(value, str):
            raise CommandError(f"Field '{key}' must be a string decimal value.")

        try:
            return Decimal(value)
        except InvalidOperation as exc:
            raise CommandError(f"Field '{key}' must be a valid decimal value.") from exc
