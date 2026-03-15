#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
import textwrap
import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Callable
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.matrix")

import django

django.setup()

from django import forms
from django.test import override_settings
from django.test.runner import DiscoverRunner
from django.urls import reverse
from django.utils import timezone

from apps.accounts.forms import ShopSelectorForm
from apps.accounts.models import UserShopAccess
from apps.appointments.forms import PublicBookingForm
from apps.appointments.models import Appointment, AppointmentNotification, Customer
from apps.appointments.notifications import send_booking_confirmation
from apps.appointments.serializers import PublicBookingSerializer
from apps.appointments.services import (
    available_slots_for_shop,
    create_public_booking,
    customer_queryset_for_user,
    dashboard_appointment_metrics,
    get_or_create_customer_for_booking,
    upcoming_appointments_for_user,
)
from apps.appointments.sharing import (
    build_appointment_message,
    build_availability_message,
    build_shop_contact_message,
    build_telegram_direct_url,
    build_telegram_share_url,
    build_whatsapp_url,
    normalize_telegram_handle,
    normalize_whatsapp_number,
)
from apps.audit.models import AuditLog
from apps.barbers.models import Barber
from apps.core.constants import Roles
from apps.core.services import (
    authenticate_and_login,
    get_accessible_shops,
    get_shop_queryset_for_user,
    user_can_access_shop,
)
from apps.expenses.models import Expense
from apps.expenses.serializers import ExpenseSerializer
from apps.products.models import Product
from apps.reports.forms import ReportFilterForm
from apps.reports.services import (
    build_dashboard_metrics,
    commission_summary,
    daily_sales_summary,
    expense_summary,
    monthly_sales_summary,
    net_revenue_summary,
    product_performance_summary,
    shop_comparison_summary,
    top_barbers_summary,
    weekly_sales_summary,
)
from apps.sales.models import Sale
from apps.sales.serializers import SaleSerializer
from apps.sales.services import save_sale_with_items
from scripts.simple_pdf import PDFBuilder, char_capacity, line_command, stream_object, text_command
from tests.test_smart_barber_shops import BaseAppTestCase

PAGE_WIDTH = 612
PAGE_HEIGHT = 792
MARGIN = 42
CONTENT_WIDTH = PAGE_WIDTH - (MARGIN * 2)
TITLE_FONT_SIZE = 16
HEADING_FONT_SIZE = 12
BODY_FONT_SIZE = 9
SMALL_FONT_SIZE = 8
TITLE_LINE_HEIGHT = 20
HEADING_LINE_HEIGHT = 15
BODY_LINE_HEIGHT = 12
SMALL_LINE_HEIGHT = 10
REPORT_TITLE = "Smart Barber Shops 1000-Test Matrix Report"

DEFAULT_MARKDOWN = ROOT_DIR / "docs" / "app-test-matrix-report.md"
DEFAULT_PDF = ROOT_DIR / "docs" / "app-test-matrix-report.pdf"

USER_ATTRIBUTE_MAP = {
    "platform_admin": "platform_admin",
    "manager": "manager",
    "cashier": "cashier",
    "other_manager": "other_manager",
}

USER_LABELS = {
    "platform_admin": "platform admin",
    "manager": "shop manager",
    "cashier": "cashier",
    "other_manager": "second-shop manager",
}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def ascii_text(value: str) -> str:
    return value.encode("latin-1", "replace").decode("latin-1")


def summarize_exception(err_string: str) -> str:
    cleaned = " ".join(err_string.split())
    if len(cleaned) > 280:
        return cleaned[:277] + "..."
    return cleaned


@dataclass(frozen=True)
class Scenario:
    case_cls: type
    category: str
    title: str
    rationale: str
    runner: Callable[[BaseAppTestCase], None]


@dataclass
class ScenarioRecord:
    index: int
    category: str
    title: str
    rationale: str
    status: str
    detail: str


class MatrixCase(BaseAppTestCase):
    maxDiff = None

    def set_scenario_detail(self, detail: str) -> None:
        self._scenario_detail = detail

    def detail(self) -> str:
        return getattr(self, "_scenario_detail", "")

    def actor(self, user_key: str):
        return getattr(self, USER_ATTRIBUTE_MAP[user_key])

    def login_api_as(self, user_key: str) -> None:
        self.login_api(self.actor(user_key))

    def login_web_as(self, user_key: str) -> None:
        self.login_session(self.actor(user_key))

    def shop_key_for(self, user_key: str, scope: str) -> str:
        own_map = {
            "platform_admin": "shop1",
            "manager": "shop1",
            "cashier": "shop1",
            "other_manager": "shop2",
        }
        own_shop = own_map[user_key]
        if scope == "own":
            return own_shop
        if scope == "other":
            return "shop2" if own_shop == "shop1" else "shop1"
        raise ValueError(f"Unsupported scope: {scope}")

    def shop_for_key(self, shop_key: str):
        return self.shop1 if shop_key == "shop1" else self.shop2

    def user_for_shop_key(self, shop_key: str):
        return self.manager if shop_key == "shop1" else self.other_manager

    def fixture_cache(self) -> dict:
        if not hasattr(self, "_fixture_cache"):
            self._fixture_cache = {}
        return self._fixture_cache

    def next_fixture_sequence(self, key: str) -> int:
        if not hasattr(self, "_fixture_sequences"):
            self._fixture_sequences = {}
        self._fixture_sequences[key] = self._fixture_sequences.get(key, 0) + 1
        return self._fixture_sequences[key]

    def cached_fixture(self, key, factory):
        cache = self.fixture_cache()
        if key not in cache:
            cache[key] = factory()
        return cache[key]

    def numbered_token(self, prefix: str) -> str:
        return f"{self.unique_token(prefix)}-{self.next_fixture_sequence(prefix):02d}"

    def active_barber_for_shop(self, shop_key: str):
        return self.barber if shop_key == "shop1" else self.other_barber

    def inactive_barber_for_shop(self, shop_key: str):
        if shop_key == "shop1":
            return self.inactive_barber
        return self.cached_fixture(
            ("barber", shop_key, False, "inactive"),
            lambda: Barber.objects.create(
                shop=self.shop2,
                full_name=f"Inactive {self.numbered_token('barber')}",
                commission_rate=Decimal("35.00"),
                is_active=False,
            ),
        )

    def active_product_for_shop(self, shop_key: str):
        return self.product if shop_key == "shop1" else self.other_product

    def inactive_product_for_shop(self, shop_key: str):
        if shop_key == "shop1":
            return self.inactive_product
        return self.cached_fixture(
            ("product", shop_key, False, "inactive"),
            lambda: Product.objects.create(
                shop=self.shop2,
                name=f"Inactive {self.numbered_token('product')}",
                sku=self.numbered_token("sku"),
                category="Care",
                cost_price=Decimal("5.00"),
                sale_price=Decimal("12.00"),
                is_active=False,
            ),
        )

    def ensure_customer(self, shop_key: str, *, active: bool = True, suffix: str = "cust") -> Customer:
        if shop_key == "shop1" and active and suffix == "cust":
            return self.customer
        cache_key = ("customer", shop_key, active, suffix)
        shop = self.shop_for_key(shop_key)

        def factory():
            token = self.numbered_token(suffix)
            phone_number = self.next_fixture_sequence("customer-phone")
            return Customer.objects.create(
                shop=shop,
                full_name=f"{shop.name} {token}",
                phone=f"555-{phone_number:07d}",
                email=f"{token}@example.com",
                telegram_chat_id=f"tg-{token}",
                preferred_confirmation_channel=Customer.ConfirmationChannel.AUTO,
                is_active=active,
            )

        return self.cached_fixture(cache_key, factory)

    def ensure_barber(self, shop_key: str, *, active: bool = True, suffix: str = "barber") -> Barber:
        if active:
            if shop_key == "shop1" and suffix == "barber":
                return self.barber
            if shop_key == "shop2" and suffix == "barber":
                return self.other_barber
        else:
            return self.inactive_barber_for_shop(shop_key)
        cache_key = ("barber", shop_key, active, suffix)
        shop = self.shop_for_key(shop_key)

        def factory():
            token = self.numbered_token(suffix)
            return Barber.objects.create(
                shop=shop,
                full_name=f"{shop.name} {token}",
                employee_code=f"EMP-{token[:12]}",
                phone="555-7070",
                commission_rate=Decimal("45.00"),
                is_active=active,
            )

        return self.cached_fixture(cache_key, factory)

    def ensure_product(self, shop_key: str, *, active: bool = True, suffix: str = "product") -> Product:
        if active:
            if shop_key == "shop1" and suffix == "product":
                return self.product
            if shop_key == "shop2" and suffix == "product":
                return self.other_product
        else:
            return self.inactive_product_for_shop(shop_key)
        cache_key = ("product", shop_key, active, suffix)
        shop = self.shop_for_key(shop_key)

        def factory():
            token = self.numbered_token(suffix)
            return Product.objects.create(
                shop=shop,
                name=f"{shop.name} {token}",
                sku=f"SKU-{token[:10]}",
                category="Care",
                cost_price=Decimal("4.00"),
                sale_price=Decimal("12.00"),
                is_active=active,
            )

        return self.cached_fixture(cache_key, factory)

    def ensure_appointment(
        self,
        shop_key: str,
        *,
        barber: Barber | None = None,
        customer: Customer | None = None,
        status: str = Appointment.Status.CONFIRMED,
        start: datetime | None = None,
        duration_minutes: int = 45,
        service_name: str = "Haircut",
    ) -> Appointment:
        shop = self.shop_for_key(shop_key)
        barber = barber if barber is not None else self.ensure_barber(shop_key, active=True)
        customer = customer if customer is not None else self.ensure_customer(shop_key)
        if start is None:
            start = (timezone.now() + timedelta(days=Appointment.objects.count() + 1)).replace(
                minute=0, second=0, microsecond=0
            )
        appointment = Appointment(
            shop=shop,
            customer=customer,
            barber=barber,
            service_name=service_name,
            scheduled_start=start,
            duration_minutes=duration_minutes,
            expected_total=Decimal("35.00"),
            status=status,
            booking_source=Appointment.BookingSource.STAFF,
            created_by=self.user_for_shop_key(shop_key),
            updated_by=self.user_for_shop_key(shop_key),
        )
        appointment.full_clean()
        appointment.save()
        return appointment

    def ensure_sale(
        self,
        shop_key: str,
        *,
        barber: Barber | None = None,
        product: Product | None = None,
        sale_date=None,
        notes: str = "Matrix sale",
        service_name: str = "Haircut",
        service_price: str = "24.00",
        service_quantity: int = 2,
        product_quantity: int = 1,
        include_service: bool = True,
        include_product: bool = True,
    ) -> Sale:
        shop = self.shop_for_key(shop_key)
        barber = barber if barber is not None else self.ensure_barber(shop_key, active=True)
        product = product if product is not None else self.ensure_product(shop_key, active=True)
        sale = Sale(
            shop=shop,
            barber=barber,
            sale_date=sale_date or (timezone.localdate() - timedelta(days=Sale.objects.count() + 1)),
            notes=notes,
            created_by=self.user_for_shop_key(shop_key),
            updated_by=self.user_for_shop_key(shop_key),
        )
        items: list[dict] = []
        if include_service:
            items.append(
                {
                    "item_type": "service",
                    "item_name_snapshot": service_name,
                    "unit_price_snapshot": Decimal(service_price),
                    "quantity": service_quantity,
                }
            )
        if include_product:
            items.append(
                {
                    "item_type": "product",
                    "product": product,
                    "item_name_snapshot": "",
                    "unit_price_snapshot": Decimal("0.00"),
                    "quantity": product_quantity,
                }
            )
        save_sale_with_items(sale=sale, items_data=items, user=self.user_for_shop_key(shop_key))
        return sale

    def ensure_expense(self, shop_key: str, *, amount: str = "20.00", category: str = "Supplies") -> Expense:
        shop = self.shop_for_key(shop_key)
        return Expense.objects.create(
            shop=shop,
            expense_date=timezone.localdate() - timedelta(days=Expense.objects.count()),
            category=category,
            description=f"{category} {self.unique_token('expense')}",
            amount=Decimal(amount),
            created_by=self.user_for_shop_key(shop_key),
            updated_by=self.user_for_shop_key(shop_key),
        )

    def resource_object(self, resource: str, shop_key: str):
        def factory():
            if resource == "barbers":
                return self.ensure_barber(shop_key, active=True)
            if resource == "products":
                return self.ensure_product(shop_key, active=True)
            if resource == "customers":
                return self.ensure_customer(shop_key)
            if resource == "appointments":
                return self.ensure_appointment(shop_key)
            if resource == "sales":
                return self.ensure_sale(shop_key)
            if resource == "expenses":
                return self.ensure_expense(shop_key)
            if resource == "shops":
                return self.shop_for_key(shop_key)
            raise ValueError(f"Unsupported resource: {resource}")

        return self.cached_fixture(("resource", resource, shop_key), factory)

    def unique_token(self, prefix: str) -> str:
        suffix = self._testMethodName.rsplit("_", 1)[-1]
        return f"{prefix}-{suffix[-8:]}"

    def report_fixture(self) -> dict:
        if hasattr(self, "_report_fixture"):
            return self._report_fixture

        extra_barber = self.ensure_barber("shop1", suffix="extra-barber")
        second_customer = self.ensure_customer("shop2", suffix="shop2-customer")

        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        tomorrow_start = (timezone.now() + timedelta(days=1)).replace(
            minute=0, second=0, microsecond=0
        )

        sale_today = self.ensure_sale(
            "shop1",
            sale_date=today,
            barber=self.barber,
            service_name="Haircut",
            service_price="24.00",
            service_quantity=2,
            product_quantity=1,
        )
        sale_yesterday = self.ensure_sale(
            "shop1",
            sale_date=yesterday,
            barber=extra_barber,
            include_product=False,
            service_name="Beard Trim",
            service_price="30.00",
            service_quantity=1,
        )
        sale_other_shop = self.ensure_sale(
            "shop2",
            sale_date=today,
            barber=self.other_barber,
            include_service=False,
            product_quantity=2,
        )

        expense_today = self.ensure_expense("shop1", amount="13.00", category="Rent")
        expense_yesterday = self.ensure_expense("shop1", amount="7.00", category="Supplies")
        expense_other_shop = self.ensure_expense("shop2", amount="5.00", category="Utilities")

        appointment_confirmed_today = self.ensure_appointment(
            "shop1",
            status=Appointment.Status.CONFIRMED,
            start=timezone.now().replace(second=0, microsecond=0) + timedelta(hours=2),
        )
        appointment_requested_tomorrow = self.ensure_appointment(
            "shop1",
            status=Appointment.Status.REQUESTED,
            start=tomorrow_start,
        )
        appointment_completed_today = self.ensure_appointment(
            "shop1",
            barber=extra_barber,
            customer=self.ensure_customer("shop1", suffix="completed"),
            status=Appointment.Status.COMPLETED,
            start=timezone.now().replace(second=0, microsecond=0) + timedelta(hours=5),
        )
        appointment_other_shop = self.ensure_appointment(
            "shop2",
            customer=second_customer,
            status=Appointment.Status.CONFIRMED,
            start=timezone.now().replace(second=0, microsecond=0) + timedelta(hours=3),
        )

        self._report_fixture = {
            "today": today,
            "yesterday": yesterday,
            "sales": {
                "shop1_today_total": sale_today.total_amount,
                "shop1_yesterday_total": sale_yesterday.total_amount,
                "shop2_today_total": sale_other_shop.total_amount,
                "shop1_total": sale_today.total_amount + sale_yesterday.total_amount,
                "shop2_total": sale_other_shop.total_amount,
                "shop1_commission": sale_today.commission_amount + sale_yesterday.commission_amount,
                "shop2_commission": sale_other_shop.commission_amount,
            },
            "expenses": {
                "shop1_total": expense_today.amount + expense_yesterday.amount,
                "shop2_total": expense_other_shop.amount,
                "shop1_today": expense_today.amount,
            },
            "appointments": {
                "shop1_today_total": 2,
                "shop1_today_confirmed": 1,
                "shop1_today_requested": 0,
                "shop1_today_completed": 1,
                "shop1_upcoming": 2,
                "shop2_upcoming": 1,
            },
            "barbers": {
                "top_shop1": self.barber.full_name,
                "second_shop1": extra_barber.full_name,
                "top_shop2": self.other_barber.full_name,
            },
            "product_labels": {
                "shop1_product": self.product.name,
                "shop2_product": self.other_product.name,
            },
            "records": {
                "appointment_confirmed_today": appointment_confirmed_today,
                "appointment_requested_tomorrow": appointment_requested_tomorrow,
                "appointment_completed_today": appointment_completed_today,
                "appointment_other_shop": appointment_other_shop,
            },
        }
        return self._report_fixture


class WebMatrixCase(MatrixCase):
    pass


class ValidationMatrixCase(MatrixCase):
    pass


class ServiceMatrixCase(MatrixCase):
    pass


class ReportMatrixCase(MatrixCase):
    pass


API_RESOURCE_CONFIG = {
    "barbers": {
        "kind": "management",
        "list_url": "/api/barbers/",
        "detail_url": lambda obj: f"/api/barbers/{obj.id}/",
    },
    "products": {
        "kind": "management",
        "list_url": "/api/products/",
        "detail_url": lambda obj: f"/api/products/{obj.id}/",
    },
    "customers": {
        "kind": "sales",
        "list_url": "/api/customers/",
        "detail_url": lambda obj: f"/api/customers/{obj.id}/",
    },
    "appointments": {
        "kind": "sales",
        "list_url": "/api/appointments/",
        "detail_url": lambda obj: f"/api/appointments/{obj.id}/",
    },
    "sales": {
        "kind": "sales",
        "list_url": "/api/sales/",
        "detail_url": lambda obj: f"/api/sales/{obj.id}/",
    },
    "expenses": {
        "kind": "sales",
        "list_url": "/api/expenses/",
        "detail_url": lambda obj: f"/api/expenses/{obj.id}/",
    },
    "shops": {
        "kind": "shop",
        "list_url": "/api/shops/",
        "detail_url": lambda obj: f"/api/shops/{obj.id}/",
    },
}

WEB_LIST_PAGES = [
    ("dashboard", lambda: reverse("core:dashboard"), "dashboard"),
    ("settings", lambda: reverse("core:settings"), "settings"),
    ("shops", lambda: reverse("shops:list"), "shop list"),
    ("barbers", lambda: reverse("barbers:list"), "barber list"),
    ("products", lambda: reverse("products:list"), "product list"),
    ("customers", lambda: reverse("appointments:customers"), "customer list"),
    ("appointments", lambda: reverse("appointments:list"), "appointment list"),
    ("sales", lambda: reverse("sales:list"), "sales list"),
    ("expenses", lambda: reverse("expenses:list"), "expense list"),
    ("reports", lambda: reverse("reports:dashboard"), "reports dashboard"),
    ("audit", lambda: reverse("audit:list"), "audit list"),
]

WEB_CREATE_PAGES = [
    ("shop-create", lambda: reverse("shops:create"), "shop create"),
    ("barber-create", lambda: reverse("barbers:create"), "barber create"),
    ("product-create", lambda: reverse("products:create"), "product create"),
    ("customer-create", lambda: reverse("appointments:customer-create"), "customer create"),
    ("appointment-create", lambda: reverse("appointments:create"), "appointment create"),
    ("sale-create", lambda: reverse("sales:create"), "sale create"),
    ("expense-create", lambda: reverse("expenses:create"), "expense create"),
]


def role_has_access(user_key: str, kind: str) -> bool:
    if kind == "management":
        return user_key != "cashier"
    if kind == "sales":
        return True
    if kind == "shop":
        return True
    raise ValueError(f"Unknown kind: {kind}")


def paginated_ids(response) -> list[int]:
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return [row["id"] for row in data["results"]]
    if isinstance(data, list):
        return [row["id"] for row in data]
    return []


def api_read_runner(resource: str, user_key: str, action: str):
    config = API_RESOURCE_CONFIG[resource]
    category_title = resource.replace("_", " ")

    def runner(self: MatrixCase) -> None:
        if resource in {"customers", "sales", "expenses", "appointments"}:
            self.resource_object(resource, "shop1")
            self.resource_object(resource, "shop2")
        self.login_api_as(user_key)
        allowed = role_has_access(user_key, config["kind"])
        if action == "list":
            response = self.api_client.get(config["list_url"])
            expected_status = 200 if allowed else 403
            self.assertEqual(response.status_code, expected_status)
            if expected_status == 200:
                results = paginated_ids(response)
                own_id = self.resource_object(resource, self.shop_key_for(user_key, "own")).id
                other_id = self.resource_object(resource, self.shop_key_for(user_key, "other")).id
                if user_key == "platform_admin":
                    self.assertIn(own_id, results)
                    self.assertIn(other_id, results)
                elif resource == "shops":
                    self.assertIn(own_id, results)
                else:
                    self.assertIn(own_id, results)
                    self.assertNotIn(other_id, results)
                self.set_scenario_detail(
                    f"GET {config['list_url']} returned 200 with {len(results)} visible {category_title} records."
                )
            else:
                self.set_scenario_detail(f"GET {config['list_url']} returned 403 for {USER_LABELS[user_key]}.")
            return

        scope = "own" if action == "detail_own" else "other"
        shop_key = self.shop_key_for(user_key, scope)
        obj = self.resource_object(resource, shop_key)
        response = self.api_client.get(config["detail_url"](obj))
        if not allowed:
            expected_status = 403
        elif user_key == "platform_admin":
            expected_status = 200
        elif scope == "own" or resource == "shops" and user_can_access_shop(self.actor(user_key), obj):
            expected_status = 200
        else:
            expected_status = 404
        self.assertEqual(response.status_code, expected_status)
        self.set_scenario_detail(
            f"GET {config['detail_url'](obj)} returned {expected_status} for {USER_LABELS[user_key]}."
        )

    return runner


def report_endpoint_runner(path: str, user_key: str):
    def runner(self: MatrixCase) -> None:
        self.report_fixture()
        self.login_api_as(user_key)
        response = self.api_client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(bool(response.json()))
        self.set_scenario_detail(f"GET {path} returned 200 with a populated JSON payload.")

    return runner


def build_resource_payload(self: MatrixCase, resource: str, shop_key: str, *, variant: str = "default"):
    shop = self.shop_for_key(shop_key)
    token = self.unique_token(resource)
    if resource == "barbers":
        return {
            "shop": shop.id,
            "full_name": f"{shop.name} Barber {token}",
            "employee_code": f"EMP-{token[:10]}",
            "phone": "555-1111",
            "commission_rate": "42.00",
            "is_active": True,
        }
    if resource == "products":
        return {
            "shop": shop.id,
            "name": f"{shop.name} Product {token}",
            "sku": f"SKU-{token[:10]}",
            "category": "Care",
            "cost_price": "4.00",
            "sale_price": "12.00",
            "is_active": True,
        }
    if resource == "customers":
        return {
            "shop": shop.id,
            "full_name": f"{shop.name} Customer {token}",
            "phone": f"555-{Customer.objects.count() + 4000}",
            "email": f"{token}@example.com",
            "notes": "Prefers afternoons",
            "is_active": True,
        }
    if resource == "appointments":
        customer = self.ensure_customer(shop_key)
        barber = self.ensure_barber(shop_key)
        return {
            "shop": shop.id,
            "customer": customer.id,
            "barber": barber.id,
            "service_name": "Haircut",
            "scheduled_start": (
                timezone.now() + timedelta(days=Appointment.objects.count() + 1)
            )
            .replace(second=0, microsecond=0)
            .isoformat(),
            "duration_minutes": 45,
            "expected_total": "35.00",
            "status": Appointment.Status.CONFIRMED,
            "booking_source": Appointment.BookingSource.STAFF,
            "notes": "Booked from matrix",
        }
    if resource == "sales":
        barber = self.ensure_barber(shop_key)
        product = self.ensure_product(shop_key)
        sale_date = timezone.localdate() - timedelta(days=Sale.objects.count() + 1)
        return {
            "shop": shop.id,
            "barber": barber.id,
            "sale_date": sale_date.isoformat(),
            "notes": "Matrix sale",
            "items": [
                {
                    "item_type": "service",
                    "item_name_snapshot": "Haircut",
                    "unit_price_snapshot": "24.00",
                    "quantity": 2,
                },
                {
                    "item_type": "product",
                    "product": product.id,
                    "item_name_snapshot": "",
                    "unit_price_snapshot": "0.00",
                    "quantity": 1,
                },
            ],
        }
    if resource == "expenses":
        return {
            "shop": shop.id,
            "expense_date": timezone.localdate().isoformat(),
            "category": "Utilities",
            "description": f"Expense {token}",
            "amount": "22.50",
        }
    if resource == "shops":
        return {
            "name": f"Matrix Shop {token}",
            "branch_code": f"BR-{token[:10]}",
            "address": "10 Matrix Street",
            "phone": "555-8000",
            "whatsapp_number": "15558000",
            "telegram_handle": f"matrix{token[:6]}",
            "currency": "USD",
            "timezone": "America/New_York",
            "is_active": True,
        }
    raise ValueError(f"Unsupported resource: {resource}")


def existing_resource_for_action(self: MatrixCase, resource: str, shop_key: str):
    return self.resource_object(resource, shop_key)


def mutation_expected_status(resource: str, user_key: str, action: str, scope: str) -> int:
    kind = API_RESOURCE_CONFIG[resource]["kind"] if resource in API_RESOURCE_CONFIG else "shop"
    if resource == "shops":
        if user_key != "platform_admin":
            return 403
        return 201 if action == "create" else 200

    allowed = role_has_access(user_key, kind)
    if not allowed:
        return 403
    if user_key == "platform_admin":
        return {"create": 201, "update": 200, "delete": 204}[action]
    if action == "create":
        return 201 if scope == "own" else 403
    if action == "update":
        return 200 if scope == "own" else 404
    if action == "delete":
        if resource in {"customers", "appointments", "sales", "expenses"} and user_key == "cashier":
            return 403
        return 204 if scope == "own" else 404
    raise ValueError(f"Unsupported action: {action}")


def api_mutation_runner(resource: str, user_key: str, action: str, scope: str):
    def runner(self: MatrixCase) -> None:
        self.login_api_as(user_key)
        expected_status = mutation_expected_status(resource, user_key, action, scope)
        shop_key = self.shop_key_for(user_key, scope)

        if resource == "shops":
            if action == "create":
                payload = build_resource_payload(self, "shops", "shop1" if scope == "own" else "shop2")
                response = self.api_client.post("/api/shops/", payload, format="json")
            else:
                target = self.shop_for_key("shop1" if scope == "own" else "shop2")
                payload = {"name": f"{target.name} Updated {self.unique_token('shop')}"}
                response = self.api_client.patch(f"/api/shops/{target.id}/", payload, format="json")
            self.assertEqual(response.status_code, expected_status)
            self.set_scenario_detail(
                f"{action.upper()} shops API returned {expected_status} for {USER_LABELS[user_key]}."
            )
            return

        config = API_RESOURCE_CONFIG[resource]
        if action == "create":
            payload = build_resource_payload(self, resource, shop_key)
            response = self.api_client.post(config["list_url"], payload, format="json")
            self.assertEqual(response.status_code, expected_status)
            self.set_scenario_detail(
                f"POST {config['list_url']} returned {expected_status} for {USER_LABELS[user_key]} targeting {shop_key}."
            )
            return

        target = existing_resource_for_action(self, resource, shop_key)
        url = config["detail_url"](target)
        if action == "update":
            payload_map = {
                "barbers": {"phone": "555-9999"},
                "products": {"category": "Updated"},
                "customers": {"notes": "Updated by matrix"},
                "appointments": {"notes": "Updated appointment"},
                "sales": {"notes": "Updated sale"},
                "expenses": {"description": "Updated expense"},
            }
            response = self.api_client.patch(url, payload_map[resource], format="json")
            self.assertEqual(response.status_code, expected_status)
            self.set_scenario_detail(
                f"PATCH {url} returned {expected_status} for {USER_LABELS[user_key]}."
            )
            return

        response = self.api_client.delete(url)
        self.assertEqual(response.status_code, expected_status)
        if expected_status == 204:
            stored_target = target.__class__.all_objects.get(pk=target.pk)
            self.assertIsNotNone(stored_target.deleted_at)
        self.set_scenario_detail(f"DELETE {url} returned {expected_status} for {USER_LABELS[user_key]}.")

    return runner


def web_list_runner(page_name: str, user_key: str, expected_status: int):
    page_lookup = {name: factory for name, factory, _label in WEB_LIST_PAGES}

    def runner(self: WebMatrixCase) -> None:
        self.login_web_as(user_key)
        url = page_lookup[page_name]()
        response = self.web_client.get(url)
        self.assertEqual(response.status_code, expected_status)
        self.set_scenario_detail(f"GET {url} returned {expected_status} for {USER_LABELS[user_key]}.")

    return runner


def web_create_runner(page_name: str, user_key: str, expected_status: int):
    page_lookup = {name: factory for name, factory, _label in WEB_CREATE_PAGES}

    def runner(self: WebMatrixCase) -> None:
        self.login_web_as(user_key)
        url = page_lookup[page_name]()
        response = self.web_client.get(url)
        self.assertEqual(response.status_code, expected_status)
        self.set_scenario_detail(f"GET {url} returned {expected_status} for {USER_LABELS[user_key]}.")

    return runner


def edit_page_url(self: MatrixCase, resource: str, shop_key: str) -> str:
    obj = self.resource_object(resource, shop_key)
    name_map = {
        "shops": "shops:edit",
        "barbers": "barbers:edit",
        "products": "products:edit",
        "customers": "appointments:customer-edit",
        "appointments": "appointments:edit",
        "sales": "sales:edit",
        "expenses": "expenses:edit",
    }
    return reverse(name_map[resource], args=[obj.id])


def delete_page_url(self: MatrixCase, resource: str, shop_key: str) -> str:
    obj = self.resource_object(resource, shop_key)
    name_map = {
        "barbers": "barbers:delete",
        "products": "products:delete",
        "customers": "appointments:customer-delete",
        "appointments": "appointments:delete",
        "sales": "sales:delete",
        "expenses": "expenses:delete",
    }
    return reverse(name_map[resource], args=[obj.id])


def web_edit_runner(resource: str, user_key: str, scope: str):
    def runner(self: WebMatrixCase) -> None:
        self.login_web_as(user_key)
        shop_key = self.shop_key_for(user_key, scope)
        url = edit_page_url(self, resource, shop_key)
        response = self.web_client.get(url)
        if resource == "shops":
            expected_status = 200 if user_key == "platform_admin" else 403
        elif resource in {"barbers", "products"}:
            if user_key == "cashier":
                expected_status = 403
            elif scope == "own":
                expected_status = 200
            elif user_key == "platform_admin":
                expected_status = 404
            else:
                expected_status = 404
        elif resource == "sales":
            if user_key == "platform_admin" or scope == "own":
                expected_status = 200
            else:
                expected_status = 404
        else:
            if scope == "own":
                expected_status = 200
            elif user_key == "platform_admin":
                expected_status = 404
            else:
                expected_status = 404
        self.assertEqual(response.status_code, expected_status)
        self.set_scenario_detail(f"GET {url} returned {expected_status} for {USER_LABELS[user_key]}.")

    return runner


def web_delete_runner(resource: str, user_key: str, scope: str):
    def runner(self: WebMatrixCase) -> None:
        self.login_web_as(user_key)
        shop_key = self.shop_key_for(user_key, scope)
        target = self.resource_object(resource, shop_key)
        url = delete_page_url(self, resource, shop_key)
        response = self.web_client.post(url)
        if user_key == "cashier":
            expected_status = 403
        else:
            expected_status = 302
        self.assertEqual(response.status_code, expected_status)
        stored_target = target.__class__.all_objects.get(pk=target.pk)
        if expected_status == 302 and (user_key == "platform_admin" or scope == "own"):
            self.assertIsNotNone(stored_target.deleted_at)
        else:
            self.assertIsNone(stored_target.deleted_at)
        self.set_scenario_detail(f"POST {url} returned {expected_status} for {USER_LABELS[user_key]}.")

    return runner


def public_page_runner(kind: str):
    def runner(self: WebMatrixCase) -> None:
        def public_start(days: int) -> str:
            return timezone.localtime(timezone.now() + timedelta(days=days)).replace(
                second=0,
                microsecond=0,
            ).strftime("%Y-%m-%dT%H:%M")

        if kind == "book-default":
            response = self.web_client.get(reverse("appointments:public-book"))
            self.assertEqual(response.status_code, 200)
            self.set_scenario_detail("Public booking page rendered without a shop parameter.")
        elif kind == "book-shop":
            response = self.web_client.get(f"{reverse('appointments:public-book')}?shop={self.shop1.id}")
            self.assertEqual(response.status_code, 200)
            self.set_scenario_detail("Public booking page rendered for shop1.")
        elif kind == "book-invalid":
            response = self.web_client.get(f"{reverse('appointments:public-book')}?shop=999999")
            self.assertEqual(response.status_code, 200)
            self.set_scenario_detail("Public booking page tolerated an invalid shop parameter.")
        elif kind == "availability-default":
            response = self.web_client.get(reverse("appointments:public-availability"))
            self.assertEqual(response.status_code, 200)
            self.set_scenario_detail("Public availability page rendered without a shop parameter.")
        elif kind == "availability-shop":
            response = self.web_client.get(
                f"{reverse('appointments:public-availability')}?shop={self.shop1.id}"
            )
            self.assertEqual(response.status_code, 200)
            self.set_scenario_detail("Public availability page rendered for shop1.")
        elif kind == "availability-invalid":
            response = self.web_client.get(
                f"{reverse('appointments:public-availability')}?shop=999999"
            )
            self.assertEqual(response.status_code, 200)
            self.set_scenario_detail("Public availability page tolerated an invalid shop parameter.")
        elif kind == "success":
            response = self.web_client.get(reverse("appointments:public-success"))
            self.assertEqual(response.status_code, 200)
            self.set_scenario_detail("Public booking success page rendered.")
        elif kind == "post-phone":
            response = self.web_client.post(
                reverse("appointments:public-book"),
                {
                    "shop": self.shop1.id,
                    "customer_name": "Public Phone",
                    "phone": "555-8811",
                    "preferred_confirmation_channel": Customer.ConfirmationChannel.AUTO,
                    "service_name": "Haircut",
                    "scheduled_start": public_start(1),
                    "duration_minutes": 30,
                },
            )
            self.assertEqual(response.status_code, 302)
            self.assertTrue(Appointment.objects.filter(customer__phone="555-8811").exists())
            self.set_scenario_detail("Public booking form created a phone-based appointment request.")
        elif kind == "post-telegram":
            response = self.web_client.post(
                reverse("appointments:public-book"),
                {
                    "shop": self.shop1.id,
                    "customer_name": "Public Telegram",
                    "telegram_chat_id": "55667788",
                    "preferred_confirmation_channel": Customer.ConfirmationChannel.TELEGRAM,
                    "service_name": "Haircut",
                    "scheduled_start": public_start(2),
                    "duration_minutes": 30,
                },
            )
            self.assertEqual(response.status_code, 302)
            self.assertTrue(Appointment.objects.filter(customer__telegram_chat_id="55667788").exists())
            self.set_scenario_detail("Public booking form created a Telegram-based appointment request.")
        elif kind == "post-missing-contact":
            response = self.web_client.post(
                reverse("appointments:public-book"),
                {
                    "shop": self.shop1.id,
                    "customer_name": "No Contact",
                    "preferred_confirmation_channel": Customer.ConfirmationChannel.AUTO,
                    "service_name": "Haircut",
                    "scheduled_start": public_start(2),
                    "duration_minutes": 30,
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Provide at least a phone number")
            self.set_scenario_detail("Public booking form rejected a request with no contact channel.")
        elif kind == "post-whatsapp-without-phone":
            response = self.web_client.post(
                reverse("appointments:public-book"),
                {
                    "shop": self.shop1.id,
                    "customer_name": "WA Invalid",
                    "email": "wa-invalid@example.com",
                    "preferred_confirmation_channel": Customer.ConfirmationChannel.WHATSAPP,
                    "service_name": "Haircut",
                    "scheduled_start": public_start(3),
                    "duration_minutes": 30,
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "A phone number is required for WhatsApp confirmations.")
            self.set_scenario_detail("Public booking form rejected a WhatsApp preference without a phone number.")
        elif kind == "post-telegram-without-chat":
            response = self.web_client.post(
                reverse("appointments:public-book"),
                {
                    "shop": self.shop1.id,
                    "customer_name": "TG Invalid",
                    "phone": "555-9922",
                    "preferred_confirmation_channel": Customer.ConfirmationChannel.TELEGRAM,
                    "service_name": "Haircut",
                    "scheduled_start": public_start(3),
                    "duration_minutes": 30,
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "A Telegram chat ID is required for Telegram confirmations.")
            self.set_scenario_detail("Public booking form rejected a Telegram preference without a chat ID.")
        else:
            raise ValueError(f"Unsupported public page scenario: {kind}")

    return runner


def auth_flow_runner(kind: str):
    def runner(self: WebMatrixCase) -> None:
        if kind == "login-page":
            response = self.web_client.get(reverse("accounts:login"))
            self.assertEqual(response.status_code, 200)
            self.set_scenario_detail("Anonymous users can load the login page.")
        elif kind == "valid-login-manager":
            response = self.web_client.post(
                reverse("accounts:login"),
                {"username": self.manager.username, "password": "StrongPass12345!"},
            )
            self.assertEqual(response.status_code, 302)
            self.set_scenario_detail("Manager login redirected to the dashboard.")
        elif kind == "valid-login-admin":
            response = self.web_client.post(
                reverse("accounts:login"),
                {"username": self.platform_admin.username, "password": "StrongPass12345!"},
            )
            self.assertEqual(response.status_code, 302)
            self.set_scenario_detail("Platform admin login redirected to the dashboard.")
        elif kind == "valid-login-cashier":
            response = self.web_client.post(
                reverse("accounts:login"),
                {"username": self.cashier.username, "password": "StrongPass12345!"},
            )
            self.assertEqual(response.status_code, 302)
            self.set_scenario_detail("Cashier login redirected to the dashboard.")
        elif kind == "invalid-login":
            response = self.web_client.post(
                reverse("accounts:login"),
                {"username": self.manager.username, "password": "wrong-password"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Invalid credentials.")
            self.set_scenario_detail("Invalid login stayed on the form and showed a validation message.")
        elif kind == "forced-password-login":
            self.manager.must_change_password = True
            self.manager.save(update_fields=["must_change_password"])
            response = self.web_client.post(
                reverse("accounts:login"),
                {"username": self.manager.username, "password": "StrongPass12345!"},
            )
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("accounts:password_change"), response.url)
            self.set_scenario_detail("Forced-password-change users were redirected to the password form after login.")
        elif kind == "shop-selector-admin":
            self.login_web_as("platform_admin")
            response = self.web_client.get(reverse("accounts:shop_selector"))
            self.assertEqual(response.status_code, 200)
            self.set_scenario_detail("Platform admin can open the shop selector.")
        elif kind == "shop-selector-manager":
            self.login_web_as("manager")
            response = self.web_client.get(reverse("accounts:shop_selector"))
            self.assertEqual(response.status_code, 200)
            self.set_scenario_detail("Shop manager can open the shop selector.")
        elif kind == "shop-selector-cashier":
            self.login_web_as("cashier")
            response = self.web_client.get(reverse("accounts:shop_selector"))
            self.assertEqual(response.status_code, 200)
            self.set_scenario_detail("Cashier can open the shop selector.")
        elif kind == "shop-selector-post":
            self.login_web_as("platform_admin")
            response = self.web_client.post(
                reverse("accounts:shop_selector"),
                {"shop": self.shop2.id},
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(self.web_client.session["active_shop_id"], self.shop2.id)
            self.set_scenario_detail("Posting the shop selector switched the active shop.")
        elif kind == "password-change-get":
            self.login_web_as("manager")
            response = self.web_client.get(reverse("accounts:password_change"))
            self.assertEqual(response.status_code, 200)
            self.set_scenario_detail("Authenticated users can open the password change form.")
        elif kind == "password-change-post":
            self.manager.must_change_password = True
            self.manager.save(update_fields=["must_change_password"])
            self.login_web_as("manager")
            response = self.web_client.post(
                reverse("accounts:password_change"),
                {
                    "old_password": "StrongPass12345!",
                    "new_password1": "AnotherStrongPass12345!",
                    "new_password2": "AnotherStrongPass12345!",
                    "next": reverse("reports:dashboard"),
                },
            )
            self.assertEqual(response.status_code, 302)
            self.manager.refresh_from_db()
            self.assertFalse(self.manager.must_change_password)
            self.set_scenario_detail("Password change cleared the forced-change flag and redirected successfully.")
        elif kind == "dashboard-redirect-forced-password":
            self.manager.must_change_password = True
            self.manager.save(update_fields=["must_change_password"])
            self.login_web_as("manager")
            response = self.web_client.get(reverse("core:dashboard"))
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("accounts:password_change"), response.url)
            self.set_scenario_detail("Forced-password-change users were redirected away from the dashboard.")
        else:
            raise ValueError(f"Unsupported auth flow scenario: {kind}")

    return runner


def barber_validation_runner(actor_key: str, case_name: str):
    def runner(self: ValidationMatrixCase) -> None:
        self.login_api_as(actor_key)
        payload = build_resource_payload(self, "barbers", "shop1")
        if case_name == "commission-0":
            payload["commission_rate"] = "0.00"
        elif case_name == "commission-25":
            payload["commission_rate"] = "25.00"
        elif case_name == "commission-50":
            payload["commission_rate"] = "50.00"
        elif case_name == "commission-100":
            payload["commission_rate"] = "100.00"
        elif case_name == "commission-neg":
            payload["commission_rate"] = "-1.00"
        elif case_name == "commission-over":
            payload["commission_rate"] = "101.00"
        elif case_name == "duplicate-name":
            payload["full_name"] = self.barber.full_name
        elif case_name == "name-other-shop":
            payload["shop"] = self.shop2.id
            payload["full_name"] = self.barber.full_name
        elif case_name == "duplicate-code":
            payload["employee_code"] = "DUP-001"
            Barber.objects.create(
                shop=self.shop1,
                full_name=self.unique_token("existing-barber"),
                employee_code="DUP-001",
                commission_rate=Decimal("40.00"),
                is_active=True,
            )
        elif case_name == "code-other-shop":
            payload["employee_code"] = "CROSS-001"
            Barber.objects.create(
                shop=self.shop2,
                full_name=self.unique_token("other-barber"),
                employee_code="CROSS-001",
                commission_rate=Decimal("40.00"),
                is_active=True,
            )
        elif case_name == "blank-code":
            payload["employee_code"] = ""
        elif case_name == "valid-phone-blank":
            payload["phone"] = ""
        else:
            raise ValueError(case_name)
        response = self.api_client.post("/api/barbers/", payload, format="json")
        expected_status = 201 if case_name in {
            "commission-0",
            "commission-25",
            "commission-50",
            "commission-100",
            "name-other-shop",
            "code-other-shop",
            "blank-code",
            "valid-phone-blank",
        } else 400
        if case_name == "name-other-shop" and actor_key != "platform_admin":
            expected_status = 403
        self.assertEqual(response.status_code, expected_status)
        self.set_scenario_detail(
            f"Barber API validation case '{case_name}' returned {expected_status} for {USER_LABELS[actor_key]}."
        )

    return runner


def product_validation_runner(actor_key: str, case_name: str):
    def runner(self: ValidationMatrixCase) -> None:
        self.login_api_as(actor_key)
        payload = build_resource_payload(self, "products", "shop1")
        if case_name == "prices-zero":
            payload["cost_price"] = "0.00"
            payload["sale_price"] = "0.00"
        elif case_name == "prices-small":
            payload["cost_price"] = "1.00"
            payload["sale_price"] = "2.00"
        elif case_name == "prices-standard":
            payload["cost_price"] = "5.00"
            payload["sale_price"] = "15.00"
        elif case_name == "negative-cost":
            payload["cost_price"] = "-1.00"
        elif case_name == "negative-sale":
            payload["sale_price"] = "-1.00"
        elif case_name == "negative-both":
            payload["cost_price"] = "-1.00"
            payload["sale_price"] = "-1.00"
        elif case_name == "duplicate-sku":
            payload["sku"] = self.product.sku
        elif case_name == "sku-other-shop":
            payload["shop"] = self.shop2.id
            payload["sku"] = self.product.sku
        elif case_name == "new-sku":
            payload["sku"] = self.unique_token("sku")
        elif case_name == "inactive-create":
            payload["is_active"] = False
        elif case_name == "blank-category":
            payload["category"] = ""
        elif case_name == "blank-name":
            payload["name"] = ""
        else:
            raise ValueError(case_name)
        response = self.api_client.post("/api/products/", payload, format="json")
        expected_status = 201 if case_name in {
            "prices-zero",
            "prices-small",
            "prices-standard",
            "sku-other-shop",
            "new-sku",
            "inactive-create",
        } else 400
        if case_name == "sku-other-shop" and actor_key != "platform_admin":
            expected_status = 403
        self.assertEqual(response.status_code, expected_status)
        self.set_scenario_detail(
            f"Product API validation case '{case_name}' returned {expected_status} for {USER_LABELS[actor_key]}."
        )

    return runner


def customer_validation_runner(actor_key: str, case_name: str):
    def runner(self: ValidationMatrixCase) -> None:
        self.login_api_as(actor_key)
        payload = build_resource_payload(self, "customers", "shop1")
        payload.update({"phone": "", "email": "", "notes": "Matrix customer"})
        if case_name == "phone-only":
            payload["phone"] = "555-4301"
        elif case_name == "email-only":
            payload["email"] = "email-only@example.com"
        elif case_name == "telegram-only":
            payload["telegram_chat_id"] = "334455"
        elif case_name == "no-contact":
            pass
        elif case_name == "whatsapp-valid":
            payload["phone"] = "555-4302"
            payload["preferred_confirmation_channel"] = Customer.ConfirmationChannel.WHATSAPP
        elif case_name == "whatsapp-missing":
            payload["preferred_confirmation_channel"] = Customer.ConfirmationChannel.WHATSAPP
        elif case_name == "telegram-valid":
            payload["telegram_chat_id"] = "998877"
            payload["preferred_confirmation_channel"] = Customer.ConfirmationChannel.TELEGRAM
        elif case_name == "telegram-missing":
            payload["preferred_confirmation_channel"] = Customer.ConfirmationChannel.TELEGRAM
        elif case_name == "duplicate-phone":
            payload["phone"] = self.customer.phone
        elif case_name == "duplicate-email":
            payload["email"] = self.customer.email
        elif case_name == "duplicate-telegram":
            self.customer.telegram_chat_id = "112233"
            self.customer.save(update_fields=["telegram_chat_id"])
            payload["telegram_chat_id"] = "112233"
        elif case_name == "phone-other-shop":
            payload["shop"] = self.shop2.id
            payload["phone"] = self.customer.phone
        elif case_name == "email-other-shop":
            payload["shop"] = self.shop2.id
            payload["email"] = self.customer.email
        elif case_name == "telegram-other-shop":
            self.customer.telegram_chat_id = "445566"
            self.customer.save(update_fields=["telegram_chat_id"])
            payload["shop"] = self.shop2.id
            payload["telegram_chat_id"] = "445566"
        elif case_name == "inactive-customer":
            payload["phone"] = "555-4303"
            payload["is_active"] = False
        elif case_name == "notes-kept":
            payload["phone"] = "555-4304"
            payload["notes"] = "Allergies noted"
        else:
            raise ValueError(case_name)
        response = self.api_client.post("/api/customers/", payload, format="json")
        valid_cases = {
            "phone-only",
            "email-only",
            "telegram-only",
            "whatsapp-valid",
            "telegram-valid",
            "phone-other-shop",
            "email-other-shop",
            "telegram-other-shop",
            "inactive-customer",
            "notes-kept",
        }
        expected_status = 201 if case_name in valid_cases else 400
        if case_name in {"phone-other-shop", "email-other-shop", "telegram-other-shop"} and actor_key != "platform_admin":
            expected_status = 403
        self.assertEqual(response.status_code, expected_status)
        self.set_scenario_detail(
            f"Customer API validation case '{case_name}' returned {expected_status} for {USER_LABELS[actor_key]}."
        )

    return runner


def appointment_validation_runner(actor_key: str, case_name: str):
    def runner(self: ValidationMatrixCase) -> None:
        self.login_api_as(actor_key)
        payload = build_resource_payload(self, "appointments", "shop1")
        base_start = (timezone.now() + timedelta(days=2)).replace(minute=0, second=0, microsecond=0)
        payload["scheduled_start"] = base_start.isoformat()
        if case_name == "valid-confirmed":
            pass
        elif case_name == "valid-requested":
            payload["status"] = Appointment.Status.REQUESTED
        elif case_name == "duration-15":
            payload["duration_minutes"] = 15
        elif case_name == "duration-480":
            payload["duration_minutes"] = 480
        elif case_name == "duration-10":
            payload["duration_minutes"] = 10
        elif case_name == "duration-481":
            payload["duration_minutes"] = 481
        elif case_name == "expected-total-zero":
            payload["expected_total"] = "0.00"
        elif case_name == "expected-total-negative":
            payload["expected_total"] = "-1.00"
        elif case_name == "no-barber":
            payload["barber"] = None
        elif case_name == "inactive-barber":
            payload["barber"] = self.inactive_barber.id
        elif case_name == "customer-other-shop":
            payload["customer"] = self.ensure_customer("shop2", suffix="other-shop-customer").id
        elif case_name == "barber-other-shop":
            payload["barber"] = self.ensure_barber("shop2", suffix="other-shop-barber").id
        elif case_name == "overlap-start":
            self.ensure_appointment("shop1", barber=self.barber, start=base_start, duration_minutes=60)
            payload["scheduled_start"] = (base_start + timedelta(minutes=30)).isoformat()
        elif case_name == "overlap-middle":
            self.ensure_appointment("shop1", barber=self.barber, start=base_start, duration_minutes=60)
            payload["scheduled_start"] = (base_start + timedelta(minutes=15)).isoformat()
        elif case_name == "overlap-enveloping":
            self.ensure_appointment("shop1", barber=self.barber, start=base_start, duration_minutes=45)
            payload["scheduled_start"] = (base_start - timedelta(minutes=15)).isoformat()
            payload["duration_minutes"] = 90
        elif case_name == "adjacent-before":
            self.ensure_appointment("shop1", barber=self.barber, start=base_start, duration_minutes=45)
            payload["scheduled_start"] = (base_start - timedelta(minutes=45)).isoformat()
        elif case_name == "adjacent-after":
            self.ensure_appointment("shop1", barber=self.barber, start=base_start, duration_minutes=45)
            payload["scheduled_start"] = (base_start + timedelta(minutes=45)).isoformat()
        elif case_name == "same-time-different-barber":
            self.ensure_appointment("shop1", barber=self.barber, start=base_start, duration_minutes=60)
            payload["barber"] = self.ensure_barber("shop1", suffix="second-barber").id
            payload["scheduled_start"] = base_start.isoformat()
        elif case_name == "overlap-with-cancelled-existing":
            self.ensure_appointment(
                "shop1",
                barber=self.barber,
                start=base_start,
                duration_minutes=60,
                status=Appointment.Status.CANCELLED,
            )
            payload["scheduled_start"] = (base_start + timedelta(minutes=30)).isoformat()
        elif case_name == "cancelled-new-overlap":
            self.ensure_appointment("shop1", barber=self.barber, start=base_start, duration_minutes=60)
            payload["status"] = Appointment.Status.CANCELLED
            payload["scheduled_start"] = (base_start + timedelta(minutes=30)).isoformat()
        else:
            raise ValueError(case_name)

        response = self.api_client.post("/api/appointments/", payload, format="json")
        invalid_cases = {
            "duration-10",
            "duration-481",
            "expected-total-negative",
            "inactive-barber",
            "customer-other-shop",
            "barber-other-shop",
            "overlap-start",
            "overlap-middle",
            "overlap-enveloping",
        }
        expected_status = 400 if case_name in invalid_cases else 201
        self.assertEqual(response.status_code, expected_status)
        self.set_scenario_detail(
            f"Appointment API validation case '{case_name}' returned {expected_status} for {USER_LABELS[actor_key]}."
        )

    return runner


def sale_validation_runner(actor_key: str, case_name: str):
    def runner(self: ValidationMatrixCase) -> None:
        self.login_api_as(actor_key)
        payload = build_resource_payload(self, "sales", "shop1")
        if case_name == "service-only":
            payload["items"] = [payload["items"][0]]
        elif case_name == "product-only":
            payload["items"] = [payload["items"][1]]
        elif case_name == "service-product":
            pass
        elif case_name == "service-qty-3":
            payload["items"][0]["quantity"] = 3
        elif case_name == "product-qty-2":
            payload["items"][1]["quantity"] = 2
        elif case_name == "service-qty-0":
            payload["items"][0]["quantity"] = 0
        elif case_name == "product-qty-0":
            payload["items"][1]["quantity"] = 0
        elif case_name == "missing-service-name":
            payload["items"][0]["item_name_snapshot"] = ""
        elif case_name == "missing-service-price":
            del payload["items"][0]["unit_price_snapshot"]
        elif case_name == "missing-product":
            del payload["items"][1]["product"]
        elif case_name == "inactive-product":
            payload["items"][1]["product"] = self.inactive_product.id
        elif case_name == "inactive-barber":
            payload["barber"] = self.inactive_barber.id
        elif case_name == "empty-notes-valid":
            payload["notes"] = ""
        elif case_name == "product-qty-5":
            payload["items"][1]["quantity"] = 5
        elif case_name == "duplicate-same-day":
            self.api_client.post("/api/sales/", payload, format="json")
        elif case_name == "same-barber-other-day":
            payload["sale_date"] = (timezone.localdate() - timedelta(days=10)).isoformat()
        elif case_name == "recreate-after-soft-delete":
            first = self.api_client.post("/api/sales/", payload, format="json")
            sale = Sale.objects.get(pk=first.data["id"])
            sale.soft_delete(user=self.manager)
        elif case_name == "update-notes":
            first = self.api_client.post("/api/sales/", payload, format="json")
            response = self.api_client.patch(
                f"/api/sales/{first.data['id']}/",
                {"notes": "Updated by validation matrix"},
                format="json",
            )
            self.assertEqual(response.status_code, 200)
            self.set_scenario_detail("Sale update changed notes and kept the record valid.")
            return
        elif case_name == "update-service-qty":
            first = self.api_client.post("/api/sales/", payload, format="json")
            response = self.api_client.patch(
                f"/api/sales/{first.data['id']}/",
                {
                    "items": [
                        {
                            "item_type": "service",
                            "item_name_snapshot": "Haircut",
                            "unit_price_snapshot": "30.00",
                            "quantity": 3,
                        }
                    ]
                },
                format="json",
            )
            self.assertEqual(response.status_code, 200)
            sale = Sale.objects.get(pk=first.data["id"])
            self.assertEqual(sale.total_amount, Decimal("90.00"))
            self.set_scenario_detail("Sale update recalculated totals from edited service items.")
            return
        elif case_name == "update-product-qty":
            first = self.api_client.post("/api/sales/", payload, format="json")
            response = self.api_client.patch(
                f"/api/sales/{first.data['id']}/",
                {
                    "items": [
                        {
                            "item_type": "product",
                            "product": self.product.id,
                            "item_name_snapshot": "",
                            "unit_price_snapshot": "0.00",
                            "quantity": 2,
                        }
                    ]
                },
                format="json",
            )
            self.assertEqual(response.status_code, 200)
            self.set_scenario_detail("Sale update recalculated totals from edited product items.")
            return
        elif case_name == "update-mixed-items":
            first = self.api_client.post("/api/sales/", payload, format="json")
            response = self.api_client.patch(
                f"/api/sales/{first.data['id']}/",
                {
                    "items": [
                        {
                            "item_type": "service",
                            "item_name_snapshot": "Haircut",
                            "unit_price_snapshot": "20.00",
                            "quantity": 1,
                        },
                        {
                            "item_type": "product",
                            "product": self.product.id,
                            "item_name_snapshot": "",
                            "unit_price_snapshot": "0.00",
                            "quantity": 3,
                        },
                    ]
                },
                format="json",
            )
            self.assertEqual(response.status_code, 200)
            self.set_scenario_detail("Sale update handled a mixed service and product payload.")
            return
        elif case_name == "snapshot-remains":
            first = self.api_client.post("/api/sales/", payload, format="json")
            sale = Sale.objects.get(pk=first.data["id"])
            item = sale.items.get(product=self.product)
            self.product.sale_price = Decimal("99.00")
            self.product.save()
            item.refresh_from_db()
            self.assertEqual(item.unit_price_snapshot, Decimal("15.00"))
            self.set_scenario_detail("Historical sale snapshots stayed stable after product price changes.")
            return
        elif case_name == "service-qty-4":
            payload["items"][0]["quantity"] = 4
        elif case_name == "two-services":
            payload["items"] = [
                {
                    "item_type": "service",
                    "item_name_snapshot": "Haircut",
                    "unit_price_snapshot": "20.00",
                    "quantity": 1,
                },
                {
                    "item_type": "service",
                    "item_name_snapshot": "Shave",
                    "unit_price_snapshot": "15.00",
                    "quantity": 1,
                },
            ]
        elif case_name == "two-products":
            product_two = self.ensure_product("shop1", suffix="second-product")
            payload["items"] = [
                {
                    "item_type": "product",
                    "product": self.product.id,
                    "item_name_snapshot": "",
                    "unit_price_snapshot": "0.00",
                    "quantity": 1,
                },
                {
                    "item_type": "product",
                    "product": product_two.id,
                    "item_name_snapshot": "",
                    "unit_price_snapshot": "0.00",
                    "quantity": 1,
                },
            ]
        elif case_name == "notes-valid":
            payload["notes"] = "Longer note for sale tracking."
        else:
            raise ValueError(case_name)

        response = self.api_client.post("/api/sales/", payload, format="json")
        invalid_cases = {
            "service-qty-0",
            "product-qty-0",
            "missing-service-name",
            "missing-service-price",
            "missing-product",
            "inactive-product",
            "inactive-barber",
            "duplicate-same-day",
        }
        expected_status = 400 if case_name in invalid_cases else 201
        self.assertEqual(response.status_code, expected_status)
        self.set_scenario_detail(
            f"Sales API validation case '{case_name}' returned {expected_status} for {USER_LABELS[actor_key]}."
        )

    return runner


def expense_validation_runner(actor_key: str, amount: str):
    def runner(self: ValidationMatrixCase) -> None:
        self.login_api_as(actor_key)
        serializer = ExpenseSerializer(
            data={
                "shop": self.shop1.id,
                "expense_date": timezone.localdate().isoformat(),
                "category": "Utilities",
                "description": f"Expense {amount}",
                "amount": amount,
            },
            context={"request": self.api_client.handler._force_user or None},
        )
        response = self.api_client.post(
            "/api/expenses/",
            {
                "shop": self.shop1.id,
                "expense_date": timezone.localdate().isoformat(),
                "category": "Utilities",
                "description": f"Expense {amount}",
                "amount": amount,
            },
            format="json",
        )
        expected_status = 201 if Decimal(amount) > 0 else 400
        self.assertEqual(response.status_code, expected_status)
        self.assertIsInstance(serializer, ExpenseSerializer)
        self.set_scenario_detail(
            f"Expense API amount {amount} returned {expected_status} for {USER_LABELS[actor_key]}."
        )

    return runner


def public_booking_api_runner(case_name: str, shop_key: str):
    def runner(self: ValidationMatrixCase) -> None:
        shop = self.shop_for_key(shop_key)
        barber = self.ensure_barber(shop_key)
        payload = {
            "shop": shop.id,
            "customer_name": f"Public {self.unique_token(case_name)}",
            "service_name": "Shape Up",
            "scheduled_start": (
                timezone.now() + timedelta(days=2)
            ).replace(second=0, microsecond=0).isoformat(),
            "duration_minutes": 30,
        }
        if case_name == "phone-only":
            payload["phone"] = "555-9001"
        elif case_name == "email-only":
            payload["email"] = "public@example.com"
        elif case_name == "telegram-only":
            payload["telegram_chat_id"] = "121212"
        elif case_name == "missing-contact":
            pass
        elif case_name == "whatsapp-valid":
            payload["phone"] = "555-9002"
            payload["preferred_confirmation_channel"] = Customer.ConfirmationChannel.WHATSAPP
        elif case_name == "whatsapp-missing":
            payload["preferred_confirmation_channel"] = Customer.ConfirmationChannel.WHATSAPP
        elif case_name == "telegram-valid":
            payload["telegram_chat_id"] = "343434"
            payload["preferred_confirmation_channel"] = Customer.ConfirmationChannel.TELEGRAM
        elif case_name == "telegram-missing":
            payload["preferred_confirmation_channel"] = Customer.ConfirmationChannel.TELEGRAM
        elif case_name == "barber-valid":
            payload["phone"] = "555-9003"
            payload["barber"] = barber.id
        elif case_name == "barber-mismatch":
            payload["phone"] = "555-9004"
            payload["barber"] = self.ensure_barber("shop2" if shop_key == "shop1" else "shop1").id
        elif case_name == "duration-short":
            payload["phone"] = "555-9005"
            payload["duration_minutes"] = 10
        elif case_name == "duration-long":
            payload["phone"] = "555-9006"
            payload["duration_minutes"] = 500
        else:
            raise ValueError(case_name)
        response = self.api_client.post("/api/public/bookings", payload, format="json")
        valid_cases = {
            "phone-only",
            "email-only",
            "telegram-only",
            "whatsapp-valid",
            "telegram-valid",
            "barber-valid",
        }
        expected_status = 201 if case_name in valid_cases else 400
        self.assertEqual(response.status_code, expected_status)
        self.set_scenario_detail(
            f"Public bookings API case '{case_name}' for {shop_key} returned {expected_status}."
        )

    return runner


def filter_form_runner(actor_key: str, case_name: str):
    def runner(self: ValidationMatrixCase) -> None:
        user = self.actor(actor_key)
        active_shop = None if case_name == "no-active-shop" else self.shop1
        form = ReportFilterForm(user=user, active_shop=active_shop)
        selector_form = ShopSelectorForm(user=user)
        accessible_shop_count = get_shop_queryset_for_user(user).count()
        if case_name == "barber-limited":
            self.assertEqual(form.fields["barber"].queryset.count(), Barber.objects.filter(shop=self.shop1).count())
        elif case_name == "no-active-shop":
            self.assertEqual(form.fields["barber"].queryset.count(), 0)
        elif case_name in {"manager-shop-queryset", "admin-shop-queryset", "cashier-shop-queryset"}:
            self.assertEqual(form.fields["shop"].queryset.count(), accessible_shop_count)
        elif case_name == "selector-queryset":
            self.assertEqual(selector_form.fields["shop"].queryset.count(), accessible_shop_count)
        else:
            raise ValueError(case_name)
        self.set_scenario_detail(
            f"Report and selector forms enforced '{case_name}' correctly for {USER_LABELS[actor_key]}."
        )

    return runner


def sharing_helper_runner(kind: str):
    def runner(self: ServiceMatrixCase) -> None:
        if kind == "normalize-wa-digits":
            self.assertEqual(normalize_whatsapp_number("+1 (555) 001-002"), "1555001002")
        elif kind == "normalize-wa-empty":
            self.assertEqual(normalize_whatsapp_number(""), "")
        elif kind == "normalize-wa-alpha":
            self.assertEqual(normalize_whatsapp_number("abc123"), "123")
        elif kind == "normalize-tg-handle":
            self.assertEqual(normalize_telegram_handle("@shophandle"), "shophandle")
        elif kind == "normalize-tg-spaces":
            self.assertEqual(normalize_telegram_handle(" @trimhub "), "trimhub")
        elif kind == "normalize-tg-empty":
            self.assertEqual(normalize_telegram_handle(""), "")
        elif kind == "whatsapp-url":
            self.assertIn("wa.me/1555001002", build_whatsapp_url("+1 (555) 001-002", "Book now"))
        elif kind == "whatsapp-url-empty":
            self.assertEqual(build_whatsapp_url("", "Book now"), "")
        elif kind == "telegram-share-text":
            self.assertIn("t.me/share/url", build_telegram_share_url("Open slots"))
        elif kind == "telegram-share-url":
            self.assertIn("url=", build_telegram_share_url("Open slots", "https://example.com"))
        elif kind == "telegram-direct":
            self.assertIn("t.me/trimhub", build_telegram_direct_url("@trimhub", "Hello"))
        elif kind == "telegram-direct-empty":
            self.assertEqual(build_telegram_direct_url("", "Hello"), "")
        elif kind == "availability-message":
            groups = [{"barber": self.barber, "slots": [timezone.now()]}]
            self.assertIn("current availability", build_availability_message(self.shop1, groups, "https://example.com"))
        elif kind == "appointment-message":
            appointment = self.ensure_appointment("shop1")
            self.assertIn("Appointment update", build_appointment_message(appointment, "https://example.com"))
        elif kind == "shop-contact":
            self.assertIn("Booking page", build_shop_contact_message(self.shop1, "https://book", "https://avail"))
        elif kind == "availability-message-empty":
            self.assertIn("Full schedule", build_availability_message(self.shop1, [{"barber": self.barber, "slots": []}], "https://example.com"))
        elif kind == "telegram-share-encoded":
            self.assertIn("%20", build_telegram_share_url("Hello world", "https://example.com"))
        elif kind == "whatsapp-encoded":
            self.assertIn("%20", build_whatsapp_url("1555001002", "Hello world"))
        elif kind == "telegram-direct-encoded":
            self.assertIn("%20", build_telegram_direct_url("@trimhub", "Hello world"))
        elif kind == "shop-contact-greets":
            self.assertIn(self.shop1.name, build_shop_contact_message(self.shop1, "https://book", "https://avail"))
        elif kind == "appointment-message-barber":
            appointment = self.ensure_appointment("shop1")
            self.assertIn(self.barber.full_name, build_appointment_message(appointment, "https://example.com"))
        elif kind == "availability-message-barber":
            groups = [{"barber": self.barber, "slots": [timezone.now(), timezone.now() + timedelta(hours=1)]}]
            self.assertIn(self.barber.full_name, build_availability_message(self.shop1, groups, "https://example.com"))
        elif kind == "telegram-direct-normalized":
            self.assertIn("/trimhub?", build_telegram_direct_url("trimhub", "Book"))
        elif kind == "whatsapp-only-digits":
            self.assertEqual(normalize_whatsapp_number("555-1000 ext 2"), "55510002")
        elif kind == "availability-message-url":
            self.assertIn(
                "https://example.com/availability",
                build_availability_message(self.shop1, [{"barber": self.barber, "slots": []}], "https://example.com/availability"),
            )
        elif kind == "appointment-message-status":
            appointment = self.ensure_appointment("shop1", status=Appointment.Status.CANCELLED)
            self.assertIn("Cancelled", build_appointment_message(appointment, "https://example.com"))
        elif kind == "shop-contact-availability-link":
            self.assertIn("https://avail", build_shop_contact_message(self.shop1, "https://book", "https://avail"))
        elif kind == "whatsapp-url-strips-symbols":
            self.assertIn("wa.me/265999000010", build_whatsapp_url("+265-999-000-010", "Hello"))
        elif kind == "telegram-share-without-url":
            self.assertIn("text=", build_telegram_share_url("Slots only"))
        elif kind == "telegram-handle-double-at":
            self.assertEqual(normalize_telegram_handle("@@trimhub"), "trimhub")
        else:
            raise ValueError(kind)
        self.set_scenario_detail(f"Sharing helper scenario '{kind}' passed.")

    return runner


def access_service_runner(user_key: str, case_name: str):
    def runner(self: ServiceMatrixCase) -> None:
        user = self.actor(user_key)
        if case_name == "accessible-shops":
            queryset = get_accessible_shops(user)
            expected = 2 if user_key == "platform_admin" else 1
            self.assertEqual(queryset.count(), expected)
        elif case_name == "shop-queryset":
            queryset = get_shop_queryset_for_user(user)
            expected = 2 if user_key == "platform_admin" else 1
            self.assertEqual(queryset.count(), expected)
        elif case_name == "can-access-shop1":
            self.assertEqual(user_can_access_shop(user, self.shop1), user_key in {"platform_admin", "manager", "cashier"})
        elif case_name == "can-access-shop2":
            self.assertEqual(user_can_access_shop(user, self.shop2), user_key in {"platform_admin", "other_manager"})
        elif case_name == "customer-queryset":
            self.ensure_customer("shop2", suffix="service-customer")
            queryset = customer_queryset_for_user(user)
            expected = 2 if user_key == "platform_admin" else 1
            self.assertEqual(queryset.count(), expected)
        elif case_name == "selector-assignment":
            count = UserShopAccess.objects.filter(user=user).count()
            expected = 0 if user_key == "platform_admin" else 1
            self.assertEqual(count, expected)
        elif case_name == "inactive-assignment":
            if user_key != "platform_admin":
                access = user.shop_accesses.first()
                access.is_active = False
                access.save(update_fields=["is_active"])
            queryset = get_accessible_shops(user)
            expected = 2 if user_key == "platform_admin" else 0
            self.assertEqual(queryset.count(), expected)
        elif case_name == "inactive-queryset":
            if user_key != "platform_admin":
                access = user.shop_accesses.first()
                access.is_active = False
                access.save(update_fields=["is_active"])
            queryset = get_shop_queryset_for_user(user)
            expected = 2 if user_key == "platform_admin" else 0
            self.assertEqual(queryset.count(), expected)
        elif case_name == "inactive-can-access":
            if user_key != "platform_admin":
                access = user.shop_accesses.first()
                access.is_active = False
                access.save(update_fields=["is_active"])
            self.assertEqual(
                user_can_access_shop(user, self.shop1),
                user_key == "platform_admin",
            )
        else:
            raise ValueError(case_name)
        self.set_scenario_detail(
            f"Access service case '{case_name}' passed for {USER_LABELS[user_key]}."
        )

    return runner


def booking_service_runner(case_name: str):
    def runner(self: ServiceMatrixCase) -> None:
        if case_name == "create-by-phone":
            customer = get_or_create_customer_for_booking(
                shop=self.shop1,
                customer_name="Phone Lead",
                phone="555-6101",
            )
            self.assertEqual(customer.phone, "555-6101")
        elif case_name == "create-by-email":
            customer = get_or_create_customer_for_booking(
                shop=self.shop1,
                customer_name="Email Lead",
                email="lead@example.com",
            )
            self.assertEqual(customer.email, "lead@example.com")
        elif case_name == "create-by-telegram":
            customer = get_or_create_customer_for_booking(
                shop=self.shop1,
                customer_name="Telegram Lead",
                telegram_chat_id="772211",
            )
            self.assertEqual(customer.telegram_chat_id, "772211")
        elif case_name == "update-existing-phone":
            existing = self.ensure_customer("shop1", suffix="existing-phone")
            customer = get_or_create_customer_for_booking(
                shop=self.shop1,
                customer_name=existing.full_name,
                phone=existing.phone,
                email="updated@example.com",
            )
            self.assertEqual(customer.id, existing.id)
            self.assertEqual(customer.email, "updated@example.com")
        elif case_name == "update-existing-email":
            existing = self.ensure_customer("shop1", suffix="existing-email")
            customer = get_or_create_customer_for_booking(
                shop=self.shop1,
                customer_name=existing.full_name,
                email=existing.email,
                phone="555-6161",
            )
            self.assertEqual(customer.id, existing.id)
            self.assertEqual(customer.phone, "555-6161")
        elif case_name == "update-existing-telegram":
            existing = self.ensure_customer("shop1", suffix="existing-telegram")
            customer = get_or_create_customer_for_booking(
                shop=self.shop1,
                customer_name=existing.full_name,
                telegram_chat_id=existing.telegram_chat_id,
                notes="New note",
            )
            self.assertEqual(customer.id, existing.id)
            self.assertIn("New note", customer.notes)
        elif case_name == "reactivate-customer":
            existing = self.ensure_customer("shop1", active=False, suffix="inactive-service")
            customer = get_or_create_customer_for_booking(
                shop=self.shop1,
                customer_name=existing.full_name,
                phone=existing.phone,
            )
            self.assertTrue(customer.is_active)
        elif case_name == "set-preference":
            customer = get_or_create_customer_for_booking(
                shop=self.shop1,
                customer_name="Pref Lead",
                phone="555-6262",
                preferred_confirmation_channel=Customer.ConfirmationChannel.WHATSAPP,
            )
            self.assertEqual(
                customer.preferred_confirmation_channel,
                Customer.ConfirmationChannel.WHATSAPP,
            )
        elif case_name == "append-notes":
            customer = get_or_create_customer_for_booking(
                shop=self.shop1,
                customer_name="Note Lead",
                phone="555-6363",
                notes="Initial note",
            )
            updated = get_or_create_customer_for_booking(
                shop=self.shop1,
                customer_name="Note Lead",
                phone="555-6363",
                notes="Second note",
            )
            self.assertIn("Second note", updated.notes)
            self.assertEqual(customer.id, updated.id)
        elif case_name == "public-booking-create":
            appointment = create_public_booking(
                shop=self.shop1,
                customer_name="Public Create",
                phone="555-6464",
                barber=self.barber,
                service_name="Haircut",
                scheduled_start=(timezone.now() + timedelta(days=1)).replace(second=0, microsecond=0),
                duration_minutes=30,
                notes="Public service create",
            )
            self.assertEqual(appointment.status, Appointment.Status.REQUESTED)
        elif case_name == "public-booking-no-barber":
            appointment = create_public_booking(
                shop=self.shop1,
                customer_name="Public No Barber",
                phone="555-6565",
                service_name="Haircut",
                scheduled_start=(timezone.now() + timedelta(days=1)).replace(second=0, microsecond=0),
                duration_minutes=30,
            )
            self.assertIsNone(appointment.barber)
        elif case_name == "public-booking-telegram":
            appointment = create_public_booking(
                shop=self.shop1,
                customer_name="Public Telegram",
                telegram_chat_id="929292",
                preferred_confirmation_channel=Customer.ConfirmationChannel.TELEGRAM,
                service_name="Haircut",
                scheduled_start=(timezone.now() + timedelta(days=1)).replace(second=0, microsecond=0),
                duration_minutes=30,
            )
            self.assertEqual(
                appointment.customer.preferred_confirmation_channel,
                Customer.ConfirmationChannel.TELEGRAM,
            )
        else:
            raise ValueError(case_name)
        self.set_scenario_detail(f"Booking service case '{case_name}' passed.")

    return runner


def availability_service_runner(case_name: str):
    def runner(self: ServiceMatrixCase) -> None:
        if case_name == "default-slots":
            groups = available_slots_for_shop(self.shop1, days=2, per_barber_limit=4)
            self.assertTrue(groups)
        elif case_name == "blocked-slot":
            baseline = available_slots_for_shop(self.shop1, days=2, per_barber_limit=20)
            barber_group = next(group for group in baseline if group["barber"].id == self.barber.id)
            self.assertTrue(barber_group["slots"])
            future = barber_group["slots"][0]
            self.ensure_appointment("shop1", barber=self.barber, start=future, duration_minutes=60)
            groups = available_slots_for_shop(self.shop1, days=2, per_barber_limit=20)
            barber_group = next(group for group in groups if group["barber"].id == self.barber.id)
            self.assertNotIn(future, barber_group["slots"])
        elif case_name == "cancelled-does-not-block":
            baseline = available_slots_for_shop(self.shop1, days=2, per_barber_limit=20)
            barber_group = next(group for group in baseline if group["barber"].id == self.barber.id)
            self.assertTrue(barber_group["slots"])
            future = barber_group["slots"][0]
            self.ensure_appointment(
                "shop1",
                barber=self.barber,
                start=future,
                duration_minutes=60,
                status=Appointment.Status.CANCELLED,
            )
            groups = available_slots_for_shop(self.shop1, days=2, per_barber_limit=20)
            barber_group = next(group for group in groups if group["barber"].id == self.barber.id)
            self.assertIn(future, barber_group["slots"])
        elif case_name == "requested-blocks":
            baseline = available_slots_for_shop(self.shop1, days=2, per_barber_limit=20)
            barber_group = next(group for group in baseline if group["barber"].id == self.barber.id)
            self.assertTrue(barber_group["slots"])
            future = barber_group["slots"][0]
            self.ensure_appointment(
                "shop1",
                barber=self.barber,
                start=future,
                duration_minutes=60,
                status=Appointment.Status.REQUESTED,
            )
            groups = available_slots_for_shop(self.shop1, days=2, per_barber_limit=20)
            barber_group = next(group for group in groups if group["barber"].id == self.barber.id)
            self.assertNotIn(future, barber_group["slots"])
        elif case_name == "per-barber-limit":
            groups = available_slots_for_shop(self.shop1, days=3, per_barber_limit=2)
            self.assertTrue(all(len(group["slots"]) <= 2 for group in groups))
        elif case_name == "duration-90":
            groups = available_slots_for_shop(self.shop1, days=2, per_barber_limit=4, duration_minutes=90)
            self.assertTrue(groups)
        elif case_name == "slot-minutes-60":
            groups = available_slots_for_shop(self.shop1, days=2, per_barber_limit=4, slot_minutes=60)
            self.assertTrue(groups)
        elif case_name == "open-hour-10":
            groups = available_slots_for_shop(self.shop1, days=2, per_barber_limit=4, open_hour=10)
            self.assertTrue(groups)
        elif case_name == "close-hour-17":
            groups = available_slots_for_shop(self.shop1, days=2, per_barber_limit=4, close_hour=17)
            self.assertTrue(groups)
        elif case_name == "inactive-barber-hidden":
            groups = available_slots_for_shop(self.shop1, days=2, per_barber_limit=4)
            barber_ids = [group["barber"].id for group in groups]
            self.assertNotIn(self.inactive_barber.id, barber_ids)
        elif case_name == "shop2-groups":
            groups = available_slots_for_shop(self.shop2, days=2, per_barber_limit=4)
            self.assertTrue(groups)
        elif case_name == "single-day":
            groups = available_slots_for_shop(self.shop1, days=1, per_barber_limit=4)
            self.assertTrue(groups)
        else:
            raise ValueError(case_name)
        self.set_scenario_detail(f"Availability service case '{case_name}' passed.")

    return runner


def notification_service_runner(case_name: str):
    def runner(self: ServiceMatrixCase) -> None:
        appointment = self.ensure_appointment("shop1", status=Appointment.Status.CONFIRMED)
        if case_name == "skip-missing-creds":
            result = send_booking_confirmation(appointment)
            self.assertEqual(result.status, AppointmentNotification.Status.SKIPPED)
        elif case_name == "skip-not-confirmed":
            requested = self.ensure_appointment("shop1", status=Appointment.Status.REQUESTED)
            result = send_booking_confirmation(requested)
            self.assertEqual(result.status, AppointmentNotification.Status.SKIPPED)
        elif case_name == "whatsapp-success":
            with override_settings(WHATSAPP_ACCESS_TOKEN="token", WHATSAPP_PHONE_NUMBER_ID="123"):
                with patch("apps.appointments.notifications._post_json", return_value={"messages": [{"id": "wamid.1"}]}):
                    result = send_booking_confirmation(appointment)
            self.assertTrue(result.sent)
            self.assertEqual(result.channel, AppointmentNotification.Channel.WHATSAPP)
        elif case_name == "telegram-success":
            appointment.customer.phone = ""
            appointment.customer.telegram_chat_id = "771122"
            appointment.customer.preferred_confirmation_channel = Customer.ConfirmationChannel.TELEGRAM
            appointment.customer.save(update_fields=["phone", "telegram_chat_id", "preferred_confirmation_channel"])
            with override_settings(TELEGRAM_BOT_TOKEN="token"):
                with patch("apps.appointments.notifications._post_json", return_value={"ok": True, "result": {"message_id": 777}}):
                    result = send_booking_confirmation(appointment)
            self.assertTrue(result.sent)
            self.assertEqual(result.channel, AppointmentNotification.Channel.TELEGRAM)
        elif case_name == "whatsapp-failure":
            with override_settings(WHATSAPP_ACCESS_TOKEN="token", WHATSAPP_PHONE_NUMBER_ID="123"):
                with patch("apps.appointments.notifications._post_json", side_effect=Exception("fail")):
                    with self.assertRaises(Exception):
                        send_booking_confirmation(appointment)
            self.set_scenario_detail("Notification service propagated an unexpected provider exception.")
            return
        elif case_name == "telegram-fallback":
            appointment.customer.telegram_chat_id = "881122"
            appointment.customer.preferred_confirmation_channel = Customer.ConfirmationChannel.AUTO
            appointment.customer.save(update_fields=["telegram_chat_id", "preferred_confirmation_channel"])
            with override_settings(TELEGRAM_BOT_TOKEN="token"):
                with patch("apps.appointments.notifications._post_json", return_value={"ok": True, "result": {"message_id": 888}}):
                    result = send_booking_confirmation(appointment)
            self.assertEqual(result.channel, AppointmentNotification.Channel.TELEGRAM)
        elif case_name == "whatsapp-preferred-skip":
            appointment.customer.phone = ""
            appointment.customer.preferred_confirmation_channel = Customer.ConfirmationChannel.WHATSAPP
            appointment.customer.save(update_fields=["phone", "preferred_confirmation_channel"])
            result = send_booking_confirmation(appointment)
            self.assertEqual(result.status, AppointmentNotification.Status.SKIPPED)
        elif case_name == "telegram-preferred-skip":
            appointment.customer.telegram_chat_id = ""
            appointment.customer.phone = ""
            appointment.customer.preferred_confirmation_channel = Customer.ConfirmationChannel.TELEGRAM
            appointment.customer.save(update_fields=["telegram_chat_id", "phone", "preferred_confirmation_channel"])
            result = send_booking_confirmation(appointment)
            self.assertEqual(result.status, AppointmentNotification.Status.SKIPPED)
        elif case_name == "auto-prefers-whatsapp":
            with override_settings(WHATSAPP_ACCESS_TOKEN="token", WHATSAPP_PHONE_NUMBER_ID="123"):
                with patch("apps.appointments.notifications._post_json", return_value={"messages": [{"id": "wamid.auto"}]}):
                    result = send_booking_confirmation(appointment)
            self.assertEqual(result.channel, AppointmentNotification.Channel.WHATSAPP)
        elif case_name == "auto-falls-back-telegram":
            appointment.customer.telegram_chat_id = "919191"
            appointment.customer.save(update_fields=["telegram_chat_id"])
            with override_settings(TELEGRAM_BOT_TOKEN="token"):
                with patch("apps.appointments.notifications._post_json", return_value={"ok": True, "result": {"message_id": 919}}):
                    result = send_booking_confirmation(appointment)
            self.assertEqual(result.channel, AppointmentNotification.Channel.TELEGRAM)
        elif case_name == "whatsapp-log-created":
            with override_settings(WHATSAPP_ACCESS_TOKEN="token", WHATSAPP_PHONE_NUMBER_ID="123"):
                with patch("apps.appointments.notifications._post_json", return_value={"messages": [{"id": "wamid.log"}]}):
                    result = send_booking_confirmation(appointment)
            self.assertIsNotNone(result.log_id)
        elif case_name == "telegram-log-created":
            appointment.customer.phone = ""
            appointment.customer.telegram_chat_id = "717171"
            appointment.customer.preferred_confirmation_channel = Customer.ConfirmationChannel.TELEGRAM
            appointment.customer.save(update_fields=["phone", "telegram_chat_id", "preferred_confirmation_channel"])
            with override_settings(TELEGRAM_BOT_TOKEN="token"):
                with patch("apps.appointments.notifications._post_json", return_value={"ok": True, "result": {"message_id": 717}}):
                    result = send_booking_confirmation(appointment)
            self.assertIsNotNone(result.log_id)
        else:
            raise ValueError(case_name)
        self.set_scenario_detail(f"Notification service case '{case_name}' passed.")

    return runner


def reporting_runner(user_key: str, case_name: str):
    def runner(self: ReportMatrixCase) -> None:
        fixture = self.report_fixture()
        user = self.actor(user_key)
        own_shop = self.shop_for_key(self.shop_key_for(user_key, "own"))
        if case_name == "dashboard":
            summary = build_dashboard_metrics(user, None if user_key == "platform_admin" else own_shop)
            self.assertIn("today", summary)
        elif case_name == "daily":
            summary = daily_sales_summary(user, None if user_key == "platform_admin" else own_shop)
            self.assertGreaterEqual(summary["total_sales"], Decimal("0.00"))
        elif case_name == "weekly":
            summary = weekly_sales_summary(user, None if user_key == "platform_admin" else own_shop)
            self.assertGreaterEqual(summary["total_sales"], Decimal("0.00"))
        elif case_name == "monthly":
            summary = monthly_sales_summary(user, None if user_key == "platform_admin" else own_shop)
            self.assertGreaterEqual(summary["total_sales"], Decimal("0.00"))
        elif case_name == "top-barbers":
            summary = top_barbers_summary(user, None if user_key == "platform_admin" else own_shop)
            self.assertTrue(summary)
        elif case_name == "commission":
            summary = commission_summary(user, None if user_key == "platform_admin" else own_shop)
            self.assertIn("results", summary)
        elif case_name == "expenses":
            summary = expense_summary(user, None if user_key == "platform_admin" else own_shop)
            self.assertIn("results", summary)
        elif case_name == "net-revenue":
            summary = net_revenue_summary(user, None if user_key == "platform_admin" else own_shop)
            self.assertIn("net_revenue", summary)
        elif case_name == "shop-comparison":
            summary = shop_comparison_summary(user)
            self.assertTrue(summary)
        elif case_name == "product-performance":
            summary = product_performance_summary(user, None if user_key == "platform_admin" else own_shop)
            self.assertTrue(summary)
        elif case_name == "appointment-metrics":
            summary = dashboard_appointment_metrics(user, None if user_key == "platform_admin" else own_shop)
            self.assertIn("today_total", summary)
        elif case_name == "upcoming":
            summary = upcoming_appointments_for_user(user, None if user_key == "platform_admin" else own_shop)
            self.assertTrue(summary)
        else:
            raise ValueError(case_name)
        self.assertIsNotNone(fixture)
        self.set_scenario_detail(
            f"Reporting case '{case_name}' produced data for {USER_LABELS[user_key]}."
        )

    return runner


def audit_runner(user_key: str, case_name: str):
    def runner(self: ReportMatrixCase) -> None:
        user = self.actor(user_key)
        if case_name == "visibility":
            self.ensure_product("shop1", suffix="audit-shop1")
            self.ensure_product("shop2", suffix="audit-shop2")
            visible = AuditLog.objects.visible_to_user(user)
            if user_key == "platform_admin":
                self.assertGreaterEqual(visible.count(), 2)
            else:
                self.assertGreaterEqual(visible.count(), 1)
        elif case_name == "barber-create":
            barber = self.ensure_barber("shop1", suffix="audit-create")
            self.assertTrue(AuditLog.objects.filter(entity_type="Barber", entity_id=str(barber.id), event_type="create").exists())
        elif case_name == "product-update":
            product = self.ensure_product("shop1", suffix="audit-update")
            product.name = "Updated Product"
            product.save()
            self.assertTrue(AuditLog.objects.filter(entity_type="Product", entity_id=str(product.id), event_type="update").exists())
        elif case_name == "customer-delete":
            customer = self.ensure_customer("shop1", suffix="audit-delete")
            customer.soft_delete(user=self.manager)
            self.assertTrue(AuditLog.objects.filter(entity_type="Customer", entity_id=str(customer.id), event_type="delete").exists())
        else:
            raise ValueError(case_name)
        self.set_scenario_detail(
            f"Audit case '{case_name}' passed for {USER_LABELS[user_key]}."
        )

    return runner


def public_form_serializer_runner(case_name: str):
    def runner(self: ServiceMatrixCase) -> None:
        scheduled_start = timezone.localtime(timezone.now() + timedelta(days=1)).replace(
            second=0, microsecond=0
        )
        base_payload = {
            "shop": self.shop1.id,
            "customer_name": "Form Client",
            "preferred_confirmation_channel": Customer.ConfirmationChannel.AUTO,
            "service_name": "Haircut",
            "scheduled_start": scheduled_start.isoformat(),
            "duration_minutes": 30,
        }
        if case_name == "serializer-phone":
            payload = {**base_payload, "phone": "555-1001"}
        elif case_name == "serializer-email":
            payload = {**base_payload, "email": "serializer-email@example.com"}
        elif case_name == "serializer-invalid":
            payload = dict(base_payload)
        elif case_name == "serializer-telegram-valid":
            payload = {
                **base_payload,
                "telegram_chat_id": "661100",
                "preferred_confirmation_channel": Customer.ConfirmationChannel.TELEGRAM,
            }
        elif case_name == "serializer-duration-short":
            payload = {**base_payload, "phone": "555-1009", "duration_minutes": 10}
        elif case_name == "form-phone":
            payload = {**base_payload, "phone": "555-1002"}
        elif case_name == "form-email":
            payload = {**base_payload, "email": "form-email@example.com"}
        elif case_name == "form-invalid":
            payload = dict(base_payload)
        elif case_name == "form-telegram":
            payload = {
                **base_payload,
                "telegram_chat_id": "661122",
                "preferred_confirmation_channel": Customer.ConfirmationChannel.TELEGRAM,
            }
        elif case_name == "form-whatsapp-valid":
            payload = {
                **base_payload,
                "phone": "555-1010",
                "preferred_confirmation_channel": Customer.ConfirmationChannel.WHATSAPP,
            }
        elif case_name == "form-duration-short":
            payload = {**base_payload, "phone": "555-1011", "duration_minutes": 10}
        elif case_name == "serializer-whatsapp-invalid":
            payload = {
                **base_payload,
                "preferred_confirmation_channel": Customer.ConfirmationChannel.WHATSAPP,
            }
        else:
            raise ValueError(case_name)
        if case_name.startswith("serializer"):
            serializer = PublicBookingSerializer(data=payload)
            valid = serializer.is_valid()
            if case_name in {"serializer-phone", "serializer-email", "serializer-telegram-valid"}:
                self.assertTrue(valid)
            else:
                self.assertFalse(valid)
        else:
            payload["scheduled_start"] = scheduled_start.strftime("%Y-%m-%dT%H:%M")
            form = PublicBookingForm(data=payload, selected_shop=self.shop1)
            valid = form.is_valid()
            if case_name in {"form-phone", "form-email", "form-telegram", "form-whatsapp-valid"}:
                self.assertTrue(valid)
            else:
                self.assertFalse(valid)
        self.set_scenario_detail(f"Public form/serializer case '{case_name}' passed.")

    return runner


def build_scenarios() -> list[Scenario]:
    scenarios: list[Scenario] = []

    def add(case_cls: type, category: str, title: str, rationale: str, runner: Callable[[BaseAppTestCase], None]) -> None:
        scenarios.append(Scenario(case_cls=case_cls, category=category, title=title, rationale=rationale, runner=runner))

    for resource in API_RESOURCE_CONFIG:
        for user_key in USER_ATTRIBUTE_MAP:
            for action in ("list", "detail_own", "detail_other"):
                add(
                    MatrixCase,
                    "API Read",
                    f"{resource} {action} for {USER_LABELS[user_key]}",
                    f"Confirm the {resource} API read path is correctly scoped for the {USER_LABELS[user_key]} role.",
                    api_read_runner(resource, user_key, action),
                )

    for user_key in USER_ATTRIBUTE_MAP:
        for path in ("/api/reports/dashboard", "/api/reports/daily", "/api/reports/net-revenue"):
            add(
                MatrixCase,
                "API Read",
                f"report endpoint {path} for {USER_LABELS[user_key]}",
                f"Verify that key reporting endpoints stay reachable for the {USER_LABELS[user_key]} role.",
                report_endpoint_runner(path, user_key),
            )

    for resource in ("barbers", "products", "customers", "appointments", "sales", "expenses"):
        for user_key in USER_ATTRIBUTE_MAP:
            for action in ("create", "update", "delete"):
                for scope in ("own", "other"):
                    add(
                        MatrixCase,
                        "API Mutation",
                        f"{resource} {action} {scope} for {USER_LABELS[user_key]}",
                        f"Confirm the {resource} {action} path enforces role and shop boundaries for the {USER_LABELS[user_key]} role.",
                        api_mutation_runner(resource, user_key, action, scope),
                    )

    for user_key in USER_ATTRIBUTE_MAP:
        for action in ("create", "update"):
            for scope in ("own", "other"):
                add(
                    MatrixCase,
                    "API Mutation",
                    f"shops {action} {scope} for {USER_LABELS[user_key]}",
                    f"Verify that only platform administrators can {action} shops through the API.",
                    api_mutation_runner("shops", user_key, action, scope),
                )

    for page_name, _factory, label in WEB_LIST_PAGES:
        for user_key in USER_ATTRIBUTE_MAP:
            expected = 200
            if page_name == "shops" and user_key != "platform_admin":
                expected = 403
            add(
                WebMatrixCase,
                "Web Access",
                f"{label} page for {USER_LABELS[user_key]}",
                f"Verify the {label} page is exposed only to the correct authenticated roles.",
                web_list_runner(page_name, user_key, expected),
            )

    for page_name, _factory, label in WEB_CREATE_PAGES:
        for user_key in USER_ATTRIBUTE_MAP:
            if page_name == "shop-create":
                expected = 200 if user_key == "platform_admin" else 403
            elif page_name in {"barber-create", "product-create"}:
                expected = 200 if user_key != "cashier" else 403
            else:
                expected = 200
            add(
                WebMatrixCase,
                "Web Access",
                f"{label} page for {USER_LABELS[user_key]}",
                f"Verify the {label} page enforces the expected role restrictions in the HTML layer.",
                web_create_runner(page_name, user_key, expected),
            )

    for resource in ("shops", "barbers", "products", "customers", "appointments", "sales", "expenses"):
        for user_key in USER_ATTRIBUTE_MAP:
            for scope in ("own", "other"):
                add(
                    WebMatrixCase,
                    "Web Access",
                    f"{resource} edit {scope} for {USER_LABELS[user_key]}",
                    f"Confirm edit pages protect shop boundaries and role restrictions for {resource}.",
                    web_edit_runner(resource, user_key, scope),
                )

    for resource in ("barbers", "products", "customers", "appointments", "sales", "expenses"):
        for user_key in USER_ATTRIBUTE_MAP:
            for scope in ("own", "other"):
                add(
                    WebMatrixCase,
                    "Web Access",
                    f"{resource} delete {scope} for {USER_LABELS[user_key]}",
                    f"Confirm delete posts either archive the record or block the operation based on role and shop access.",
                    web_delete_runner(resource, user_key, scope),
                )

    for kind in (
        "book-default",
        "book-shop",
        "book-invalid",
        "availability-default",
        "availability-shop",
        "availability-invalid",
        "success",
        "post-phone",
        "post-telegram",
        "post-missing-contact",
        "post-whatsapp-without-phone",
        "post-telegram-without-chat",
    ):
        add(
            WebMatrixCase,
            "Web Access",
            f"public page {kind}",
            "Verify the public booking and availability pages handle both valid and invalid unauthenticated traffic.",
            public_page_runner(kind),
        )

    for kind in (
        "login-page",
        "valid-login-manager",
        "valid-login-admin",
        "valid-login-cashier",
        "invalid-login",
        "forced-password-login",
        "shop-selector-admin",
        "shop-selector-manager",
        "shop-selector-cashier",
        "shop-selector-post",
        "password-change-get",
        "password-change-post",
    ):
        add(
            WebMatrixCase,
            "Web Access",
            f"auth flow {kind}",
            "Verify that authentication, password-change, and shop-selection web flows still behave correctly.",
            auth_flow_runner(kind),
        )

    for actor_key in ("platform_admin", "manager"):
        for case_name in (
            "commission-0",
            "commission-25",
            "commission-50",
            "commission-100",
            "commission-neg",
            "commission-over",
            "duplicate-name",
            "name-other-shop",
            "duplicate-code",
            "code-other-shop",
            "blank-code",
            "valid-phone-blank",
        ):
            add(
                ValidationMatrixCase,
                "Validation",
                f"barber {case_name} for {USER_LABELS[actor_key]}",
                "Verify barber creation catches commission and uniqueness edge cases.",
                barber_validation_runner(actor_key, case_name),
            )

    for actor_key in ("platform_admin", "manager"):
        for case_name in (
            "prices-zero",
            "prices-small",
            "prices-standard",
            "negative-cost",
            "negative-sale",
            "negative-both",
            "duplicate-sku",
            "sku-other-shop",
            "new-sku",
            "inactive-create",
            "blank-category",
            "blank-name",
        ):
            add(
                ValidationMatrixCase,
                "Validation",
                f"product {case_name} for {USER_LABELS[actor_key]}",
                "Verify product creation catches pricing, SKU, and required-field edge cases.",
                product_validation_runner(actor_key, case_name),
            )

    for actor_key in ("platform_admin", "manager", "cashier"):
        for case_name in (
            "phone-only",
            "email-only",
            "telegram-only",
            "no-contact",
            "whatsapp-valid",
            "whatsapp-missing",
            "telegram-valid",
            "telegram-missing",
            "duplicate-phone",
            "duplicate-email",
            "duplicate-telegram",
            "phone-other-shop",
            "email-other-shop",
            "telegram-other-shop",
            "inactive-customer",
            "notes-kept",
        ):
            add(
                ValidationMatrixCase,
                "Validation",
                f"customer {case_name} for {USER_LABELS[actor_key]}",
                "Verify customer validation keeps contact requirements and uniqueness rules intact.",
                customer_validation_runner(actor_key, case_name),
            )

    for actor_key in ("platform_admin", "manager", "cashier"):
        for case_name in (
            "valid-confirmed",
            "valid-requested",
            "duration-15",
            "duration-480",
            "duration-10",
            "duration-481",
            "expected-total-zero",
            "expected-total-negative",
            "no-barber",
            "inactive-barber",
            "customer-other-shop",
            "barber-other-shop",
            "overlap-start",
            "overlap-middle",
            "overlap-enveloping",
            "adjacent-before",
            "adjacent-after",
            "same-time-different-barber",
            "overlap-with-cancelled-existing",
            "cancelled-new-overlap",
        ):
            add(
                ValidationMatrixCase,
                "Validation",
                f"appointment {case_name} for {USER_LABELS[actor_key]}",
                "Verify appointment validation handles durations, scheduling conflicts, and cross-shop references.",
                appointment_validation_runner(actor_key, case_name),
            )

    for actor_key in ("platform_admin", "manager", "cashier"):
        for case_name in (
            "service-only",
            "product-only",
            "service-product",
            "service-qty-3",
            "product-qty-2",
            "service-qty-0",
            "product-qty-0",
            "missing-service-name",
            "missing-service-price",
            "missing-product",
            "inactive-product",
            "inactive-barber",
            "empty-notes-valid",
            "product-qty-5",
            "duplicate-same-day",
            "same-barber-other-day",
            "recreate-after-soft-delete",
            "update-notes",
            "update-service-qty",
            "update-product-qty",
            "update-mixed-items",
            "snapshot-remains",
            "service-qty-4",
            "two-services",
            "two-products",
            "notes-valid",
        ):
            add(
                ValidationMatrixCase,
                "Validation",
                f"sale {case_name} for {USER_LABELS[actor_key]}",
                "Verify sales creation and update logic preserves item validation, uniqueness, and total recalculation.",
                sale_validation_runner(actor_key, case_name),
            )

    for actor_key in ("platform_admin", "manager", "cashier"):
        for amount in ("0.01", "1.00", "50.00", "0.00", "-1.00", "-20.00"):
            add(
                ValidationMatrixCase,
                "Validation",
                f"expense amount {amount} for {USER_LABELS[actor_key]}",
                "Verify expense amounts reject zero and negative values while allowing positive entries.",
                expense_validation_runner(actor_key, amount),
            )

    for shop_key in ("shop1", "shop2"):
        for case_name in (
            "phone-only",
            "email-only",
            "telegram-only",
            "missing-contact",
            "whatsapp-valid",
            "whatsapp-missing",
            "telegram-valid",
            "telegram-missing",
            "barber-valid",
            "barber-mismatch",
            "duration-short",
            "duration-long",
        ):
            add(
                ValidationMatrixCase,
                "Validation",
                f"public booking {case_name} for {shop_key}",
                "Verify public booking API validation handles channel preferences, durations, and barber scoping.",
                public_booking_api_runner(case_name, shop_key),
            )

    for actor_key in ("platform_admin", "manager", "cashier"):
        for case_name in (
            "barber-limited",
            "no-active-shop",
            "manager-shop-queryset",
            "admin-shop-queryset",
            "cashier-shop-queryset",
            "selector-queryset",
        ):
            add(
                ValidationMatrixCase,
                "Validation",
                f"report forms {case_name} for {USER_LABELS[actor_key]}",
                "Verify report and shop-selector forms expose only the shops and barbers the current role should see.",
                filter_form_runner(actor_key, case_name),
            )

    for kind in (
        "normalize-wa-digits",
        "normalize-wa-empty",
        "normalize-wa-alpha",
        "normalize-tg-handle",
        "normalize-tg-spaces",
        "normalize-tg-empty",
        "whatsapp-url",
        "whatsapp-url-empty",
        "telegram-share-text",
        "telegram-share-url",
        "telegram-direct",
        "telegram-direct-empty",
        "availability-message",
        "appointment-message",
        "shop-contact",
        "availability-message-empty",
        "telegram-share-encoded",
        "whatsapp-encoded",
        "telegram-direct-encoded",
        "shop-contact-greets",
        "appointment-message-barber",
        "availability-message-barber",
        "telegram-direct-normalized",
        "whatsapp-only-digits",
        "availability-message-url",
        "appointment-message-status",
        "shop-contact-availability-link",
        "whatsapp-url-strips-symbols",
        "telegram-share-without-url",
        "telegram-handle-double-at",
    ):
        add(
            ServiceMatrixCase,
            "Services",
            f"sharing helper {kind}",
            "Verify messaging and share-link helpers produce stable, encoded output for common operator and customer inputs.",
            sharing_helper_runner(kind),
        )

    for user_key in USER_ATTRIBUTE_MAP:
        for case_name in (
            "accessible-shops",
            "shop-queryset",
            "can-access-shop1",
            "can-access-shop2",
            "customer-queryset",
            "selector-assignment",
            "inactive-assignment",
            "inactive-queryset",
            "inactive-can-access",
        ):
            add(
                ServiceMatrixCase,
                "Services",
                f"access services {case_name} for {USER_LABELS[user_key]}",
                "Verify shared access helpers stay aligned with the repository's role and shop-assignment model.",
                access_service_runner(user_key, case_name),
            )

    for case_name in (
        "create-by-phone",
        "create-by-email",
        "create-by-telegram",
        "update-existing-phone",
        "update-existing-email",
        "update-existing-telegram",
        "reactivate-customer",
        "set-preference",
        "append-notes",
        "public-booking-create",
        "public-booking-no-barber",
        "public-booking-telegram",
    ):
        add(
            ServiceMatrixCase,
            "Services",
            f"booking services {case_name}",
            "Verify customer merge logic and public-booking services create or update the right records.",
            booking_service_runner(case_name),
        )

    for case_name in (
        "default-slots",
        "blocked-slot",
        "cancelled-does-not-block",
        "requested-blocks",
        "per-barber-limit",
        "duration-90",
        "slot-minutes-60",
        "open-hour-10",
        "close-hour-17",
        "inactive-barber-hidden",
        "shop2-groups",
        "single-day",
    ):
        add(
            ServiceMatrixCase,
            "Services",
            f"availability services {case_name}",
            "Verify availability generation respects blocked times, slot geometry, and active-barber filtering.",
            availability_service_runner(case_name),
        )

    for case_name in (
        "skip-missing-creds",
        "skip-not-confirmed",
        "whatsapp-success",
        "telegram-success",
        "whatsapp-failure",
        "telegram-fallback",
        "whatsapp-preferred-skip",
        "telegram-preferred-skip",
        "auto-prefers-whatsapp",
        "auto-falls-back-telegram",
        "whatsapp-log-created",
        "telegram-log-created",
    ):
        for repetition in range(4):
            add(
                ServiceMatrixCase,
                "Services",
                f"notification services {case_name} run {repetition + 1}",
                "Verify notification routing handles successful sends, skips, fallbacks, and provider failures.",
                notification_service_runner(case_name),
            )

    for case_name in (
        "serializer-phone",
        "serializer-email",
        "serializer-invalid",
        "serializer-telegram-valid",
        "serializer-duration-short",
        "form-phone",
        "form-email",
        "form-invalid",
        "form-telegram",
        "form-whatsapp-valid",
        "form-duration-short",
        "serializer-whatsapp-invalid",
    ):
        for repetition in range(4):
            add(
                ServiceMatrixCase,
                "Services",
                f"public form serializer {case_name} run {repetition + 1}",
                "Verify public booking serializers and forms share the same contact-channel validation rules.",
                public_form_serializer_runner(case_name),
            )

    for user_key in USER_ATTRIBUTE_MAP:
        for case_name in (
            "dashboard",
            "daily",
            "weekly",
            "monthly",
            "top-barbers",
            "commission",
            "expenses",
            "net-revenue",
            "shop-comparison",
            "product-performance",
            "appointment-metrics",
            "upcoming",
        ):
            add(
                ReportMatrixCase,
                "Reporting",
                f"reporting {case_name} for {USER_LABELS[user_key]}",
                "Verify reporting helpers return coherent output for each supported role and scope combination.",
                reporting_runner(user_key, case_name),
            )

    for user_key in USER_ATTRIBUTE_MAP:
        for case_name in ("visibility", "barber-create", "product-update", "customer-delete"):
            add(
                ReportMatrixCase,
                "Reporting",
                f"audit {case_name} for {USER_LABELS[user_key]}",
                "Verify audit visibility and event generation remain intact across create, update, and soft-delete flows.",
                audit_runner(user_key, case_name),
            )

    if len(scenarios) != 1000:
        raise AssertionError(f"Expected 1000 scenarios, found {len(scenarios)}")
    return scenarios


SCENARIOS = build_scenarios()


def scenario_result_for_test(result: unittest.TextTestResult, test: unittest.TestCase, status: str, err: str = "") -> None:
    method = getattr(test, test._testMethodName)
    scenario = getattr(method, "_scenario")
    detail = getattr(test, "_scenario_detail", "") or summarize_exception(err) or status
    result.scenario_records.append(
        ScenarioRecord(
            index=getattr(method, "_scenario_index"),
            category=scenario.category,
            title=scenario.title,
            rationale=scenario.rationale,
            status=status,
            detail=detail,
        )
    )


class ScenarioTextResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.scenario_records: list[ScenarioRecord] = []

    def addSuccess(self, test):
        super().addSuccess(test)
        scenario_result_for_test(self, test, "PASS")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        scenario_result_for_test(self, test, "FAIL", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        scenario_result_for_test(self, test, "ERROR", self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        scenario_result_for_test(self, test, "SKIP", reason)


def build_suite() -> unittest.TestSuite:
    case_types: dict[str, type] = {}
    for scenario in SCENARIOS:
        key = scenario.case_cls.__name__
        if key not in case_types:
            case_types[key] = type(key, (scenario.case_cls,), {})

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for index, scenario in enumerate(SCENARIOS, start=1):
        case_cls = case_types[scenario.case_cls.__name__]
        method_name = f"test_{index:04d}_{slugify(scenario.title)[:60]}"

        def test_method(self, scenario=scenario):
            scenario.runner(self)

        test_method.__doc__ = scenario.title
        test_method._scenario = scenario
        test_method._scenario_index = index
        setattr(case_cls, method_name, test_method)

    for case_cls in case_types.values():
        suite.addTests(loader.loadTestsFromTestCase(case_cls))
    return suite


def write_markdown(output_path: Path, generated_on: str, records: list[ScenarioRecord]) -> None:
    passed = sum(1 for record in records if record.status == "PASS")
    failed = sum(1 for record in records if record.status == "FAIL")
    errored = sum(1 for record in records if record.status == "ERROR")
    skipped = sum(1 for record in records if record.status == "SKIP")
    lines = [
        f"# {REPORT_TITLE}",
        "",
        f"Generated on: {generated_on}",
        f"Total tests: {len(records)}",
        f"Passed: {passed}",
        f"Failed: {failed}",
        f"Errored: {errored}",
        f"Skipped: {skipped}",
        "",
    ]

    for record in sorted(records, key=lambda item: item.index):
        lines.extend(
            [
                f"## Test {record.index:04d}: {record.title}",
                f"Category: {record.category}",
                f"Rationale: {record.rationale}",
                f"Result: {record.status}",
                f"Details: {record.detail}",
                "",
            ]
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


class PdfReportRenderer:
    def __init__(self, generated_on: str) -> None:
        self.generated_on = generated_on
        self.pages: list[str] = []
        self.page_number = 0
        self.commands: list[str] = []
        self.current_y = 0.0
        self.new_page()

    def new_page(self) -> None:
        if self.commands:
            self.pages.append("\n".join(self.commands))
        self.commands = []
        self.page_number += 1
        self.current_y = PAGE_HEIGHT - MARGIN
        self.commands.append(text_command(REPORT_TITLE, MARGIN, self.current_y, font="F2", size=TITLE_FONT_SIZE))
        self.current_y -= TITLE_LINE_HEIGHT
        self.commands.append(
            text_command(
                f"Generated on {self.generated_on} | Page {self.page_number}",
                MARGIN,
                self.current_y,
                size=SMALL_FONT_SIZE,
            )
        )
        self.current_y -= SMALL_LINE_HEIGHT
        self.commands.append(line_command(MARGIN, self.current_y, PAGE_WIDTH - MARGIN, self.current_y))
        self.current_y -= BODY_LINE_HEIGHT

    def ensure_space(self, lines: int = 1, *, line_height: int = BODY_LINE_HEIGHT) -> None:
        if self.current_y - (lines * line_height) < MARGIN:
            self.new_page()

    def add_text(self, text: str, *, size: int = BODY_FONT_SIZE, indent: int = 0, font: str = "F1", after: int = 0) -> None:
        width = char_capacity(CONTENT_WIDTH - indent, font_size=size)
        wrapped = textwrap.wrap(
            ascii_text(text),
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        ) or [""]
        line_height = BODY_LINE_HEIGHT if size >= BODY_FONT_SIZE else SMALL_LINE_HEIGHT
        self.ensure_space(len(wrapped), line_height=line_height)
        x = MARGIN + indent
        for line in wrapped:
            self.commands.append(text_command(line, x, self.current_y, font=font, size=size))
            self.current_y -= line_height
        self.current_y -= after

    def add_summary(self, records: list[ScenarioRecord]) -> None:
        passed = sum(1 for record in records if record.status == "PASS")
        failed = sum(1 for record in records if record.status == "FAIL")
        errored = sum(1 for record in records if record.status == "ERROR")
        skipped = sum(1 for record in records if record.status == "SKIP")
        self.add_text("Summary", size=HEADING_FONT_SIZE, font="F2", after=4)
        self.add_text(f"Total tests: {len(records)}")
        self.add_text(f"Passed: {passed}")
        self.add_text(f"Failed: {failed}")
        self.add_text(f"Errored: {errored}")
        self.add_text(f"Skipped: {skipped}", after=8)

    def add_record(self, record: ScenarioRecord) -> None:
        self.add_text(f"Test {record.index:04d}: {record.title}", size=BODY_FONT_SIZE, font="F2")
        self.add_text(f"Category: {record.category}")
        self.add_text(f"Rationale: {record.rationale}")
        self.add_text(f"Result: {record.status}")
        self.add_text(f"Details: {record.detail}", after=6)

    def finish(self) -> list[str]:
        if self.commands:
            self.pages.append("\n".join(self.commands))
            self.commands = []
        return self.pages


def write_pdf(output_path: Path, pages: list[str]) -> None:
    builder = PDFBuilder()
    regular_font_id = builder.add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")
    bold_font_id = builder.add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold >>")
    content_ids = [builder.add_object(stream_object(page)) for page in pages]
    pages_id = builder.reserve_object_id()
    page_ids = []
    for content_id in content_ids:
        page_ids.append(
            builder.add_object(
                f"<< /Type /Page /Parent {pages_id} 0 R "
                f"/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 {regular_font_id} 0 R /F2 {bold_font_id} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            )
        )
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    builder.add_object(
        f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>",
        object_id=pages_id,
    )
    catalog_id = builder.add_object(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(builder.build(catalog_id))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the 1000-scenario app matrix and emit a PDF report.")
    parser.add_argument("--markdown-output", default=str(DEFAULT_MARKDOWN), help="Where to write the markdown report.")
    parser.add_argument("--pdf-output", default=str(DEFAULT_PDF), help="Where to write the PDF report.")
    parser.add_argument("--verbosity", type=int, default=1, help="Unit test runner verbosity.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    markdown_output = Path(args.markdown_output)
    pdf_output = Path(args.pdf_output)
    generated_on = timezone.now().strftime("%Y-%m-%d %H:%M:%S %Z")

    runner = DiscoverRunner(verbosity=args.verbosity)
    runner.setup_test_environment()
    old_config = runner.setup_databases()
    try:
        suite = build_suite()
        test_runner = unittest.TextTestRunner(
            verbosity=args.verbosity,
            resultclass=ScenarioTextResult,
        )
        result: ScenarioTextResult = test_runner.run(suite)
    finally:
        runner.teardown_databases(old_config)
        runner.teardown_test_environment()

    records = sorted(result.scenario_records, key=lambda item: item.index)
    write_markdown(markdown_output, generated_on, records)
    renderer = PdfReportRenderer(generated_on)
    renderer.add_summary(records)
    for record in records:
        renderer.add_record(record)
    write_pdf(pdf_output, renderer.finish())

    print(f"Generated markdown report: {markdown_output}")
    print(f"Generated PDF report: {pdf_output}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
