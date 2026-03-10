from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import UserShopAccess
from apps.appointments.models import Appointment, AppointmentNotification, Customer
from apps.appointments.services import available_slots_for_shop
from apps.appointments.sharing import (
    build_telegram_direct_url,
    build_telegram_share_url,
    build_whatsapp_url,
)
from apps.audit.models import AuditLog
from apps.barbers.models import Barber
from apps.core.constants import Roles
from apps.expenses.models import Expense
from apps.products.models import Product
from apps.reports.services import (
    daily_sales_summary,
    monthly_sales_summary,
    net_revenue_summary,
    top_barbers_summary,
    weekly_sales_summary,
)
from apps.sales.models import Sale
from apps.shops.models import Shop


class BaseAppTestCase(TestCase):
    def setUp(self):
        super().setUp()
        User = get_user_model()
        self.shop1 = Shop.objects.create(
            name="Main Branch",
            branch_code="MAIN-001",
            address="1 Main St",
            phone="555-1000",
            whatsapp_number="15551000",
            telegram_handle="mainbranchbarber",
            currency="USD",
            timezone="America/New_York",
        )
        self.shop2 = Shop.objects.create(
            name="West Branch",
            branch_code="WEST-001",
            address="2 West St",
            phone="555-2000",
            whatsapp_number="15552000",
            telegram_handle="westbranchbarber",
            currency="USD",
            timezone="America/New_York",
        )
        self.platform_admin = User.objects.create_user(
            username="admin",
            password="StrongPass12345!",
            role=Roles.PLATFORM_ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self.manager = User.objects.create_user(
            username="manager",
            password="StrongPass12345!",
            role=Roles.SHOP_MANAGER,
            is_staff=True,
        )
        self.cashier = User.objects.create_user(
            username="cashier",
            password="StrongPass12345!",
            role=Roles.CASHIER,
        )
        self.other_manager = User.objects.create_user(
            username="othermanager",
            password="StrongPass12345!",
            role=Roles.SHOP_MANAGER,
        )
        UserShopAccess.objects.create(user=self.manager, shop=self.shop1)
        UserShopAccess.objects.create(user=self.cashier, shop=self.shop1)
        UserShopAccess.objects.create(user=self.other_manager, shop=self.shop2)
        self.barber = Barber.objects.create(
            shop=self.shop1,
            full_name="Alex Barber",
            commission_rate=Decimal("40.00"),
            is_active=True,
        )
        self.inactive_barber = Barber.objects.create(
            shop=self.shop1,
            full_name="Inactive Barber",
            commission_rate=Decimal("35.00"),
            is_active=False,
        )
        self.other_barber = Barber.objects.create(
            shop=self.shop2,
            full_name="West Barber",
            commission_rate=Decimal("50.00"),
            is_active=True,
        )
        self.product = Product.objects.create(
            shop=self.shop1,
            name="Pomade",
            sku="SKU-001",
            category="Styling",
            cost_price=Decimal("5.00"),
            sale_price=Decimal("15.00"),
            is_active=True,
        )
        self.inactive_product = Product.objects.create(
            shop=self.shop1,
            name="Inactive Shampoo",
            sku="SKU-002",
            category="Care",
            cost_price=Decimal("6.00"),
            sale_price=Decimal("16.00"),
            is_active=False,
        )
        self.other_product = Product.objects.create(
            shop=self.shop2,
            name="West Product",
            sku="WEST-001",
            category="Styling",
            cost_price=Decimal("4.00"),
            sale_price=Decimal("10.00"),
            is_active=True,
        )
        self.customer = Customer.objects.create(
            shop=self.shop1,
            full_name="Chris Client",
            phone="555-3000",
            email="client@example.com",
            is_active=True,
        )
        self.web_client = Client()
        self.api_client = APIClient()

    def login_session(self, user):
        self.web_client.force_login(user)
        session = self.web_client.session
        if user.role != Roles.PLATFORM_ADMIN:
            access = user.shop_accesses.first()
            session["active_shop_id"] = access.shop_id
            session.save()

    def login_api(self, user):
        self.api_client.force_login(user)
        session = self.api_client.session
        if user.role != Roles.PLATFORM_ADMIN:
            access = user.shop_accesses.first()
            session["active_shop_id"] = access.shop_id
            session.save()

    def sale_payload(self, *, barber=None, product=None):
        return {
            "shop": self.shop1.id,
            "barber": (barber or self.barber).id,
            "sale_date": timezone.localdate().isoformat(),
            "notes": "Busy shift",
            "items": [
                {
                    "item_type": "service",
                    "item_name_snapshot": "Haircut",
                    "unit_price_snapshot": "24.00",
                    "quantity": 2,
                },
                {
                    "item_type": "product",
                    "product": (product or self.product).id,
                    "item_name_snapshot": "",
                    "unit_price_snapshot": "0.00",
                    "quantity": 1,
                },
            ],
        }

    def appointment_payload(
        self,
        *,
        customer=None,
        barber=None,
        scheduled_start=None,
        duration_minutes=45,
        status="confirmed",
    ):
        start = scheduled_start or (timezone.now() + timedelta(hours=2)).replace(
            second=0, microsecond=0
        )
        return {
            "shop": self.shop1.id,
            "customer": (customer or self.customer).id,
            "barber": (barber or self.barber).id,
            "service_name": "Haircut and Beard Trim",
            "scheduled_start": start.isoformat(),
            "duration_minutes": duration_minutes,
            "expected_total": "35.00",
            "status": status,
            "booking_source": "staff",
            "notes": "VIP client",
        }


class AuthAndAuthorizationTests(BaseAppTestCase):
    def test_unauthenticated_appointments_redirect_to_login(self):
        response = self.web_client.get(reverse("appointments:list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_create_superuser_defaults_to_platform_admin_role(self):
        User = get_user_model()
        admin = User.objects.create_superuser(
            username="bootstrapadmin",
            email="bootstrapadmin@example.com",
            password="StrongPass12345!",
        )
        self.assertEqual(admin.role, Roles.PLATFORM_ADMIN)

    def test_valid_login(self):
        response = self.web_client.post(
            reverse("accounts:login"),
            {"username": "manager", "password": "StrongPass12345!"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.web_client.session)

    def test_login_redirects_to_password_change_when_required(self):
        self.manager.must_change_password = True
        self.manager.save(update_fields=["must_change_password"])

        response = self.web_client.post(
            f"{reverse('accounts:login')}?next={reverse('reports:dashboard')}",
            {"username": "manager", "password": "StrongPass12345!"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            f"{reverse('accounts:password_change')}?next={reverse('reports:dashboard')}",
        )

    def test_locked_user_is_redirected_until_password_changes(self):
        self.manager.must_change_password = True
        self.manager.save(update_fields=["must_change_password"])
        self.login_session(self.manager)

        response = self.web_client.get(reverse("core:dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            f"{reverse('accounts:password_change')}?next={reverse('core:dashboard')}",
        )

    def test_password_change_clears_flag_and_redirects_to_original_target(self):
        self.manager.must_change_password = True
        self.manager.save(update_fields=["must_change_password"])
        self.login_session(self.manager)

        response = self.web_client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "StrongPass12345!",
                "new_password1": "NewStrongPass12345!",
                "new_password2": "NewStrongPass12345!",
                "next": reverse("reports:dashboard"),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("reports:dashboard"))
        self.assertIn("_auth_user_id", self.web_client.session)

        self.manager.refresh_from_db()
        self.assertFalse(self.manager.must_change_password)
        self.assertTrue(self.manager.check_password("NewStrongPass12345!"))

    def test_locked_user_api_requests_are_blocked(self):
        self.manager.must_change_password = True
        self.manager.save(update_fields=["must_change_password"])
        self.login_api(self.manager)

        response = self.api_client.get("/api/reports/dashboard")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"detail": "Password change required."})

    def test_invalid_login_rejected(self):
        response = self.web_client.post(
            reverse("accounts:login"),
            {"username": "manager", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid credentials.")

    def test_unauthorized_cross_shop_api_access_blocked(self):
        self.login_api(self.manager)
        response = self.api_client.get(f"/api/barbers/{self.other_barber.id}/")
        self.assertEqual(response.status_code, 404)

    def test_role_restriction_enforced_for_expense_delete(self):
        expense = Expense.objects.create(
            shop=self.shop1,
            expense_date=timezone.localdate(),
            category="Supplies",
            description="Clips",
            amount=Decimal("20.00"),
            created_by=self.manager,
            updated_by=self.manager,
        )
        self.login_api(self.cashier)
        response = self.api_client.delete(f"/api/expenses/{expense.id}/")
        self.assertEqual(response.status_code, 403)

    def test_cashier_without_active_shop_hides_shop_scoped_navigation(self):
        self.web_client.force_login(self.cashier)

        response = self.web_client.get(reverse("core:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("accounts:shop_selector"))
        self.assertContains(response, reverse("reports:dashboard"))
        self.assertContains(response, reverse("audit:list"))
        self.assertNotContains(response, reverse("appointments:customers"))
        self.assertNotContains(response, reverse("appointments:list"))
        self.assertNotContains(response, reverse("barbers:list"))
        self.assertNotContains(response, reverse("products:list"))
        self.assertNotContains(response, reverse("sales:list"))
        self.assertNotContains(response, reverse("expenses:list"))
        self.assertNotContains(response, reverse("appointments:create"))
        self.assertNotContains(response, reverse("sales:create"))

    def test_cashier_sees_only_allowed_page_actions(self):
        self.login_session(self.cashier)

        customer_response = self.web_client.get(reverse("appointments:customers"))
        self.assertEqual(customer_response.status_code, 200)
        self.assertContains(customer_response, reverse("appointments:customer-create"))
        self.assertContains(
            customer_response,
            reverse("appointments:customer-edit", args=[self.customer.pk]),
        )
        self.assertNotContains(
            customer_response,
            reverse("appointments:customer-delete", args=[self.customer.pk]),
        )

        barber_response = self.web_client.get(reverse("barbers:list"))
        self.assertEqual(barber_response.status_code, 200)
        self.assertNotContains(barber_response, reverse("barbers:create"))
        self.assertNotContains(barber_response, reverse("barbers:edit", args=[self.barber.pk]))
        self.assertNotContains(
            barber_response,
            reverse("barbers:delete", args=[self.barber.pk]),
        )


class BarberTests(BaseAppTestCase):
    def test_create_barber_succeeds(self):
        self.login_api(self.manager)
        response = self.api_client.post(
            "/api/barbers/",
            {
                "shop": self.shop1.id,
                "full_name": "Chris Fade",
                "employee_code": "EMP-100",
                "phone": "555-8888",
                "commission_rate": "42.00",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Barber.objects.filter(full_name="Chris Fade", shop=self.shop1).exists())

    def test_duplicate_barber_blocked(self):
        self.login_api(self.manager)
        response = self.api_client.post(
            "/api/barbers/",
            {
                "shop": self.shop1.id,
                "full_name": "Alex Barber",
                "employee_code": "",
                "phone": "",
                "commission_rate": "30.00",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_commission_blocked(self):
        self.login_api(self.manager)
        response = self.api_client.post(
            "/api/barbers/",
            {
                "shop": self.shop1.id,
                "full_name": "Bad Rate",
                "commission_rate": "120.00",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_inactive_barber_cannot_receive_sale(self):
        self.login_api(self.manager)
        response = self.api_client.post(
            "/api/sales/", self.sale_payload(barber=self.inactive_barber), format="json"
        )
        self.assertEqual(response.status_code, 400)


class ProductTests(BaseAppTestCase):
    def test_create_product_succeeds(self):
        self.login_api(self.manager)
        response = self.api_client.post(
            "/api/products/",
            {
                "shop": self.shop1.id,
                "name": "Aftershave",
                "sku": "SKU-003",
                "category": "Care",
                "cost_price": "3.00",
                "sale_price": "10.00",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Product.objects.filter(sku="SKU-003", shop=self.shop1).exists())

    def test_duplicate_sku_blocked(self):
        self.login_api(self.manager)
        response = self.api_client.post(
            "/api/products/",
            {
                "shop": self.shop1.id,
                "name": "Duplicate Pomade",
                "sku": "SKU-001",
                "category": "Styling",
                "cost_price": "5.00",
                "sale_price": "15.00",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_inactive_product_cannot_be_sold(self):
        self.login_api(self.manager)
        response = self.api_client.post(
            "/api/sales/", self.sale_payload(product=self.inactive_product), format="json"
        )
        self.assertEqual(response.status_code, 400)


class MessagingAndAvailabilityTests(BaseAppTestCase):
    def test_whatsapp_and_telegram_helpers_create_links(self):
        whatsapp_url = build_whatsapp_url("555-3000", "Available schedule")
        telegram_share_url = build_telegram_share_url(
            "Available schedule",
            "https://example.com/availability",
        )
        telegram_direct_url = build_telegram_direct_url("@barbershop", "Need an appointment")
        self.assertIn("wa.me/5553000", whatsapp_url)
        self.assertIn("t.me/share/url", telegram_share_url)
        self.assertIn("t.me/barbershop", telegram_direct_url)

    def test_available_slots_skip_existing_appointment(self):
        tz = ZoneInfo(self.shop1.timezone)
        scheduled_start = datetime.combine(
            timezone.localdate() + timedelta(days=1),
            datetime.min.time().replace(hour=10),
            tzinfo=tz,
        )
        Appointment.objects.create(
            shop=self.shop1,
            customer=self.customer,
            barber=self.barber,
            service_name="Haircut",
            scheduled_start=scheduled_start,
            duration_minutes=60,
            expected_total=Decimal("30.00"),
            status=Appointment.Status.CONFIRMED,
            booking_source=Appointment.BookingSource.STAFF,
            created_by=self.manager,
            updated_by=self.manager,
        )
        groups = available_slots_for_shop(self.shop1, days=2, per_barber_limit=8)
        barber_group = next(group for group in groups if group["barber"].id == self.barber.id)
        self.assertNotIn(scheduled_start, barber_group["slots"])

    def test_public_availability_api_returns_slots(self):
        response = self.web_client.get(f"/api/public/availability?shop={self.shop1.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["shop"], self.shop1.name)
        self.assertIn("availability", response.json())

    def test_customer_list_contains_schedule_share_links(self):
        self.login_session(self.manager)
        response = self.web_client.get(reverse("appointments:customers"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "wa.me")
        self.assertContains(response, "t.me/share/url")


class CustomerAndAppointmentTests(BaseAppTestCase):
    def test_create_customer_succeeds(self):
        self.login_api(self.manager)
        response = self.api_client.post(
            "/api/customers/",
            {
                "shop": self.shop1.id,
                "full_name": "Dana Fade",
                "phone": "555-4400",
                "email": "dana@example.com",
                "notes": "Prefers afternoon slots",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Customer.objects.filter(full_name="Dana Fade", shop=self.shop1).exists())

    def test_customer_requires_contact_method(self):
        self.login_api(self.manager)
        response = self.api_client.post(
            "/api/customers/",
            {
                "shop": self.shop1.id,
                "full_name": "No Contact",
                "phone": "",
                "email": "",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_appointment_succeeds(self):
        self.login_api(self.manager)
        response = self.api_client.post(
            "/api/appointments/", self.appointment_payload(), format="json"
        )
        self.assertEqual(response.status_code, 201)
        appointment = Appointment.objects.get(pk=response.data["id"])
        self.assertEqual(appointment.status, Appointment.Status.CONFIRMED)
        self.assertEqual(appointment.booking_source, Appointment.BookingSource.STAFF)

    @override_settings(
        WHATSAPP_ACCESS_TOKEN="test-wa-token",
        WHATSAPP_PHONE_NUMBER_ID="123456789",
    )
    @patch("apps.appointments.notifications._post_json")
    def test_confirmed_appointment_sends_whatsapp_confirmation(self, post_json):
        post_json.return_value = {"messages": [{"id": "wamid.123"}]}
        self.login_api(self.manager)
        response = self.api_client.post(
            "/api/appointments/", self.appointment_payload(), format="json"
        )
        self.assertEqual(response.status_code, 201)
        notification = AppointmentNotification.objects.get(appointment_id=response.data["id"])
        self.assertEqual(notification.status, AppointmentNotification.Status.SENT)
        self.assertEqual(notification.channel, AppointmentNotification.Channel.WHATSAPP)
        self.assertEqual(notification.provider_message_id, "wamid.123")
        post_json.assert_called_once()

    @override_settings(TELEGRAM_BOT_TOKEN="test-telegram-token")
    @patch("apps.appointments.notifications._post_json")
    def test_confirming_requested_appointment_sends_telegram_confirmation(self, post_json):
        post_json.return_value = {"ok": True, "result": {"message_id": 98765}}
        telegram_customer = Customer.objects.create(
            shop=self.shop1,
            full_name="Telegram Client",
            telegram_chat_id="99887766",
            preferred_confirmation_channel=Customer.ConfirmationChannel.TELEGRAM,
            is_active=True,
        )
        appointment = Appointment.objects.create(
            shop=self.shop1,
            customer=telegram_customer,
            barber=self.barber,
            service_name="Line Up",
            scheduled_start=(timezone.now() + timedelta(days=1)).replace(second=0, microsecond=0),
            duration_minutes=30,
            expected_total=Decimal("20.00"),
            status=Appointment.Status.REQUESTED,
            booking_source=Appointment.BookingSource.ONLINE,
            created_by=self.manager,
            updated_by=self.manager,
        )
        self.login_api(self.manager)
        response = self.api_client.patch(
            f"/api/appointments/{appointment.id}/",
            {"status": Appointment.Status.CONFIRMED},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        notification = AppointmentNotification.objects.get(appointment=appointment)
        self.assertEqual(notification.status, AppointmentNotification.Status.SENT)
        self.assertEqual(notification.channel, AppointmentNotification.Channel.TELEGRAM)
        self.assertEqual(notification.provider_message_id, "98765")
        post_json.assert_called_once()

    def test_overlapping_appointment_blocked(self):
        self.login_api(self.manager)
        start = (timezone.now() + timedelta(hours=4)).replace(second=0, microsecond=0)
        first = self.appointment_payload(scheduled_start=start, duration_minutes=60)
        second = self.appointment_payload(
            scheduled_start=start + timedelta(minutes=30),
            duration_minutes=30,
        )
        self.api_client.post("/api/appointments/", first, format="json")
        response = self.api_client.post("/api/appointments/", second, format="json")
        self.assertEqual(response.status_code, 400)

    def test_public_booking_creates_requested_appointment(self):
        response = self.api_client.post(
            "/api/public/bookings",
            {
                "shop": self.shop1.id,
                "customer_name": "Walk In Client",
                "phone": "555-7755",
                "email": "walkin@example.com",
                "barber": self.barber.id,
                "service_name": "Shape Up",
                "scheduled_start": (timezone.now() + timedelta(days=1))
                .replace(second=0, microsecond=0)
                .isoformat(),
                "duration_minutes": 30,
                "notes": "Prefers morning",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        appointment = Appointment.objects.get(pk=response.data["id"])
        self.assertEqual(appointment.status, Appointment.Status.REQUESTED)
        self.assertEqual(appointment.booking_source, Appointment.BookingSource.ONLINE)
        self.assertEqual(appointment.customer.phone, "555-7755")

    def test_public_booking_accepts_telegram_confirmation_details(self):
        response = self.api_client.post(
            "/api/public/bookings",
            {
                "shop": self.shop1.id,
                "customer_name": "Telegram Lead",
                "phone": "",
                "email": "",
                "telegram_chat_id": "44556677",
                "preferred_confirmation_channel": Customer.ConfirmationChannel.TELEGRAM,
                "barber": self.barber.id,
                "service_name": "Shape Up",
                "scheduled_start": (timezone.now() + timedelta(days=2))
                .replace(second=0, microsecond=0)
                .isoformat(),
                "duration_minutes": 30,
                "notes": "Telegram only",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        appointment = Appointment.objects.get(pk=response.data["id"])
        self.assertEqual(
            appointment.customer.preferred_confirmation_channel,
            Customer.ConfirmationChannel.TELEGRAM,
        )
        self.assertEqual(appointment.customer.telegram_chat_id, "44556677")


class SalesTests(BaseAppTestCase):
    def test_create_sale_succeeds_and_calculates_totals(self):
        self.login_api(self.manager)
        response = self.api_client.post("/api/sales/", self.sale_payload(), format="json")
        self.assertEqual(response.status_code, 201)
        sale = Sale.objects.get(pk=response.data["id"])
        self.assertEqual(sale.total_amount, Decimal("63.00"))
        self.assertEqual(sale.commission_amount, Decimal("25.20"))

    def test_duplicate_daily_sale_blocked(self):
        self.login_api(self.manager)
        self.api_client.post("/api/sales/", self.sale_payload(), format="json")
        response = self.api_client.post("/api/sales/", self.sale_payload(), format="json")
        self.assertEqual(response.status_code, 400)

    def test_editing_sale_recalculates_correctly(self):
        self.login_api(self.manager)
        create_response = self.api_client.post("/api/sales/", self.sale_payload(), format="json")
        sale_id = create_response.data["id"]
        response = self.api_client.patch(
            f"/api/sales/{sale_id}/",
            {
                "notes": "Updated",
                "items": [
                    {
                        "item_type": "service",
                        "item_name_snapshot": "Haircut",
                        "unit_price_snapshot": "30.00",
                        "quantity": 3,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        sale = Sale.objects.get(pk=sale_id)
        self.assertEqual(sale.total_amount, Decimal("90.00"))
        self.assertEqual(sale.commission_amount, Decimal("36.00"))

    def test_product_price_change_does_not_change_historical_snapshot(self):
        self.login_api(self.manager)
        create_response = self.api_client.post("/api/sales/", self.sale_payload(), format="json")
        sale = Sale.objects.get(pk=create_response.data["id"])
        product_item = sale.items.get(product=self.product)
        self.product.sale_price = Decimal("99.00")
        self.product.save()
        product_item.refresh_from_db()
        self.assertEqual(product_item.unit_price_snapshot, Decimal("15.00"))


class ExpenseAndReportTests(BaseAppTestCase):
    def setUp(self):
        super().setUp()
        self.login_api(self.manager)
        self.api_client.post("/api/sales/", self.sale_payload(), format="json")

    def test_create_expense_succeeds(self):
        response = self.api_client.post(
            "/api/expenses/",
            {
                "shop": self.shop1.id,
                "expense_date": timezone.localdate().isoformat(),
                "category": "Utilities",
                "description": "Electricity bill",
                "amount": "22.50",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_invalid_amount_rejected(self):
        response = self.api_client.post(
            "/api/expenses/",
            {
                "shop": self.shop1.id,
                "expense_date": timezone.localdate().isoformat(),
                "category": "Utilities",
                "description": "Invalid amount",
                "amount": "-1.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_expense_affects_net_revenue_reports(self):
        Expense.objects.create(
            shop=self.shop1,
            expense_date=timezone.localdate(),
            category="Rent",
            description="March rent",
            amount=Decimal("13.00"),
            created_by=self.manager,
            updated_by=self.manager,
        )
        summary = net_revenue_summary(self.manager, self.shop1)
        self.assertEqual(summary["net_revenue"], Decimal("24.80"))

    def test_daily_weekly_monthly_and_top_barber_reports_are_accurate(self):
        daily = daily_sales_summary(self.manager, self.shop1)
        weekly = weekly_sales_summary(self.manager, self.shop1)
        monthly = monthly_sales_summary(self.manager, self.shop1)
        top_barbers = top_barbers_summary(self.manager, self.shop1)
        self.assertEqual(daily["total_sales"], Decimal("63.00"))
        self.assertEqual(weekly["total_sales"], Decimal("63.00"))
        self.assertEqual(monthly["total_sales"], Decimal("63.00"))
        self.assertEqual(top_barbers[0]["barber__full_name"], "Alex Barber")


class AuditTests(BaseAppTestCase):
    def test_audit_log_written_on_create_update_delete(self):
        product = Product.objects.create(
            shop=self.shop1,
            name="Wax",
            sku="SKU-010",
            category="Styling",
            cost_price=Decimal("2.00"),
            sale_price=Decimal("8.00"),
            is_active=True,
        )
        product.name = "Wax Plus"
        product.save()
        product.soft_delete(user=self.manager)
        events = list(
            AuditLog.objects.filter(entity_type="Product", entity_id=str(product.id)).values_list(
                "event_type", flat=True
            )
        )
        self.assertIn("create", events)
        self.assertIn("update", events)
        self.assertIn("delete", events)


class GoLiveInitializationCommandTests(TestCase):
    def write_config(self, payload):
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        self.addCleanup(lambda: os.path.exists(handle.name) and os.unlink(handle.name))
        with handle:
            json.dump(payload, handle)
        return handle.name

    def test_initialize_golive_creates_required_records(self):
        payload = {
            "platform_admin": {
                "username": "platformadmin",
                "email": "admin@example.com",
                "password": "StrongPass12345!",
                "must_change_password": True,
            },
            "shops": [
                {
                    "branch_code": "BLZ-001",
                    "name": "Machinjiri Barber Lounge",
                    "address": "101 Example Road",
                    "phone": "+265-999-000-010",
                    "currency": "MWK",
                    "timezone": "Africa/Blantyre",
                    "users": [
                        {
                            "username": "owner-machinjiri",
                            "email": "owner@example.com",
                            "password": "StrongPass12345!",
                            "role": Roles.SHOP_OWNER,
                            "must_change_password": True,
                        }
                    ],
                    "barbers": [
                        {
                            "full_name": "Alex Banda",
                            "employee_code": "BR-001",
                            "commission_rate": "45.00",
                        }
                    ],
                    "products": [
                        {
                            "sku": "POM-001",
                            "name": "Signature Pomade",
                            "category": "Styling",
                            "sale_price": "12000.00",
                        }
                    ],
                }
            ],
        }

        call_command("initialize_golive", config=self.write_config(payload))

        User = get_user_model()
        admin = User.objects.get(username="platformadmin")
        owner = User.objects.get(username="owner-machinjiri")
        shop = Shop.objects.get(branch_code="BLZ-001")

        self.assertEqual(admin.role, Roles.PLATFORM_ADMIN)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.check_password("StrongPass12345!"))
        self.assertEqual(owner.role, Roles.SHOP_OWNER)
        self.assertTrue(
            UserShopAccess.objects.filter(user=owner, shop=shop, is_active=True).exists()
        )
        self.assertTrue(
            Barber.objects.filter(shop=shop, employee_code="BR-001", is_active=True).exists()
        )
        self.assertTrue(Product.objects.filter(shop=shop, sku="POM-001", is_active=True).exists())

    def test_initialize_golive_does_not_reset_existing_passwords_without_flag(self):
        User = get_user_model()
        existing_admin = User.objects.create_user(
            username="platformadmin",
            email="admin@example.com",
            password="OldPass12345!",
            role=Roles.PLATFORM_ADMIN,
            is_staff=True,
            is_superuser=True,
        )

        payload = {
            "platform_admin": {
                "username": "platformadmin",
                "email": "admin@example.com",
                "password": "NewPass12345!",
            },
            "shops": [
                {
                    "branch_code": "BLZ-001",
                    "name": "Machinjiri Barber Lounge",
                    "address": "101 Example Road",
                    "phone": "+265-999-000-010",
                    "users": [
                        {
                            "username": "cashier-machinjiri",
                            "email": "cashier@example.com",
                            "password": "CashierPass12345!",
                            "role": Roles.CASHIER,
                        }
                    ],
                    "barbers": [{"full_name": "Alex Banda"}],
                }
            ],
        }

        call_command("initialize_golive", config=self.write_config(payload))

        existing_admin.refresh_from_db()
        self.assertTrue(existing_admin.check_password("OldPass12345!"))
        self.assertFalse(existing_admin.check_password("NewPass12345!"))

    def test_initialize_golive_requires_operator_and_barber_for_active_shop(self):
        User = get_user_model()
        User.objects.create_user(
            username="platformadmin",
            email="admin@example.com",
            password="StrongPass12345!",
            role=Roles.PLATFORM_ADMIN,
            is_staff=True,
            is_superuser=True,
        )

        payload = {
            "shops": [
                {
                    "branch_code": "BLZ-001",
                    "name": "Machinjiri Barber Lounge",
                    "address": "101 Example Road",
                    "phone": "+265-999-000-010",
                    "users": [
                        {
                            "username": "barber-login",
                            "email": "barber@example.com",
                            "password": "StrongPass12345!",
                            "role": Roles.BARBER,
                        }
                    ],
                    "barbers": [],
                }
            ]
        }

        with self.assertRaisesMessage(
            CommandError,
            "must have at least one active shop_owner, shop_manager, or cashier user.",
        ):
            call_command("initialize_golive", config=self.write_config(payload))
