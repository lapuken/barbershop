from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import UserShopAccess
from apps.appointments.models import Appointment, Customer
from apps.barbers.models import Barber
from apps.core.constants import Roles
from apps.expenses.models import Expense
from apps.products.models import Product
from apps.sales.models import Sale
from apps.sales.services import save_sale_with_items
from apps.shops.models import Shop


class Command(BaseCommand):
    help = "Seed a richer demo dataset for Smart Barber Shops."

    def handle(self, *args, **options):
        User = get_user_model()
        admin, _ = User.objects.get_or_create(
            username="platformadmin",
            defaults={"email": "admin@example.com", "role": Roles.PLATFORM_ADMIN, "is_staff": True, "is_superuser": True},
        )
        admin.set_password("ChangeMe12345!")
        admin.save()

        shop, _ = Shop.objects.get_or_create(
            branch_code="NYC-001",
            defaults={
                "name": "Downtown Barber Lounge",
                "address": "100 Main Street, New York, NY",
                "phone": "+1-555-0100",
                "whatsapp_number": "15550100",
                "telegram_handle": "downtownbarberlounge",
                "currency": "USD",
                "timezone": "America/New_York",
            },
        )
        owner, _ = User.objects.get_or_create(
            username="owner1",
            defaults={"email": "owner@example.com", "role": Roles.SHOP_OWNER, "is_staff": True},
        )
        owner.set_password("ChangeMe12345!")
        owner.save()
        UserShopAccess.objects.get_or_create(user=owner, shop=shop)

        manager, _ = User.objects.get_or_create(
            username="manager1",
            defaults={"email": "manager@example.com", "role": Roles.SHOP_MANAGER, "is_staff": True},
        )
        manager.set_password("ChangeMe12345!")
        manager.save()
        UserShopAccess.objects.get_or_create(user=manager, shop=shop)

        cashier, _ = User.objects.get_or_create(
            username="cashier1",
            defaults={"email": "cashier@example.com", "role": Roles.CASHIER},
        )
        cashier.set_password("ChangeMe12345!")
        cashier.save()
        UserShopAccess.objects.get_or_create(user=cashier, shop=shop)

        shop_two, _ = Shop.objects.get_or_create(
            branch_code="NYC-002",
            defaults={
                "name": "Uptown Barber Studio",
                "address": "200 Uptown Avenue, New York, NY",
                "phone": "+1-555-0200",
                "whatsapp_number": "15550200",
                "telegram_handle": "uptownbarberstudio",
                "currency": "USD",
                "timezone": "America/New_York",
            },
        )
        owner_two, _ = User.objects.get_or_create(
            username="owner2",
            defaults={"email": "owner2@example.com", "role": Roles.SHOP_OWNER, "is_staff": True},
        )
        owner_two.set_password("ChangeMe12345!")
        owner_two.save()
        UserShopAccess.objects.get_or_create(user=owner_two, shop=shop_two)

        barber_one, _ = Barber.objects.get_or_create(
            shop=shop,
            full_name="Jordan Miles",
            defaults={"commission_rate": Decimal("45.00"), "phone": "+1-555-0111"},
        )
        barber_two, _ = Barber.objects.get_or_create(
            shop=shop,
            full_name="Marcus Reed",
            defaults={"commission_rate": Decimal("40.00"), "phone": "+1-555-0112"},
        )
        barber_three, _ = Barber.objects.get_or_create(
            shop=shop_two,
            full_name="Avery Cole",
            defaults={"commission_rate": Decimal("42.50"), "phone": "+1-555-0211"},
        )

        product_one, _ = Product.objects.get_or_create(
            shop=shop,
            sku="POMADE-001",
            defaults={
                "name": "Signature Pomade",
                "category": "Styling",
                "cost_price": Decimal("4.00"),
                "sale_price": Decimal("12.00"),
            },
        )
        product_two, _ = Product.objects.get_or_create(
            shop=shop,
            sku="BEARD-001",
            defaults={
                "name": "Beard Oil",
                "category": "Care",
                "cost_price": Decimal("5.50"),
                "sale_price": Decimal("16.00"),
            },
        )
        product_three, _ = Product.objects.get_or_create(
            shop=shop_two,
            sku="CLAY-001",
            defaults={
                "name": "Matte Clay",
                "category": "Styling",
                "cost_price": Decimal("4.50"),
                "sale_price": Decimal("14.00"),
            },
        )

        customer_one, _ = Customer.objects.get_or_create(
            shop=shop,
            phone="+1-555-1010",
            defaults={
                "full_name": "Nia Thompson",
                "email": "nia@example.com",
                "notes": "Usually books after work.",
            },
        )
        customer_two, _ = Customer.objects.get_or_create(
            shop=shop,
            phone="+1-555-1011",
            defaults={
                "full_name": "Caleb Brooks",
                "email": "caleb@example.com",
            },
        )
        customer_three, _ = Customer.objects.get_or_create(
            shop=shop_two,
            phone="+1-555-2010",
            defaults={
                "full_name": "Maya Ellis",
                "email": "maya@example.com",
            },
        )

        today = timezone.localdate()
        now = timezone.now().replace(second=0, microsecond=0)
        sale_rows = [
            (
                shop,
                barber_one,
                manager,
                today,
                [
                    {"item_type": "service", "item_name_snapshot": "Haircut", "unit_price_snapshot": Decimal("28.00"), "quantity": 4},
                    {"item_type": "service", "item_name_snapshot": "Beard Trim", "unit_price_snapshot": Decimal("18.00"), "quantity": 2},
                    {"item_type": "product", "product": product_one, "item_name_snapshot": "", "unit_price_snapshot": Decimal("0.00"), "quantity": 2},
                ],
            ),
            (
                shop,
                barber_two,
                cashier,
                today - timedelta(days=1),
                [
                    {"item_type": "service", "item_name_snapshot": "Haircut", "unit_price_snapshot": Decimal("26.00"), "quantity": 3},
                    {"item_type": "product", "product": product_two, "item_name_snapshot": "", "unit_price_snapshot": Decimal("0.00"), "quantity": 1},
                ],
            ),
            (
                shop,
                barber_one,
                manager,
                today - timedelta(days=2),
                [
                    {"item_type": "service", "item_name_snapshot": "Haircut", "unit_price_snapshot": Decimal("28.00"), "quantity": 2},
                    {"item_type": "service", "item_name_snapshot": "Hot Towel Shave", "unit_price_snapshot": Decimal("30.00"), "quantity": 1},
                ],
            ),
            (
                shop_two,
                barber_three,
                owner_two,
                today,
                [
                    {"item_type": "service", "item_name_snapshot": "Haircut", "unit_price_snapshot": Decimal("30.00"), "quantity": 3},
                    {"item_type": "product", "product": product_three, "item_name_snapshot": "", "unit_price_snapshot": Decimal("0.00"), "quantity": 2},
                ],
            ),
        ]

        for sale_shop, sale_barber, actor, sale_date, items in sale_rows:
            sale, _ = Sale.objects.get_or_create(
                shop=sale_shop,
                barber=sale_barber,
                sale_date=sale_date,
                defaults={
                    "created_by": actor,
                    "updated_by": actor,
                    "notes": "Seeded demo sale",
                },
            )
            if not sale.items.exists():
                save_sale_with_items(sale=sale, items_data=items, user=actor)

        expense_rows = [
            (shop, today, "Supplies", "Clipper guards and combs", Decimal("42.00"), manager),
            (shop, today - timedelta(days=1), "Utilities", "Laundry and electricity", Decimal("58.50"), manager),
            (shop, today - timedelta(days=3), "Cleaning", "Shop cleaning services", Decimal("35.00"), cashier),
            (shop_two, today, "Supplies", "Styling stock replenishment", Decimal("47.25"), owner_two),
        ]

        for expense_shop, expense_date, category, description, amount, actor in expense_rows:
            Expense.objects.get_or_create(
                shop=expense_shop,
                expense_date=expense_date,
                category=category,
                description=description,
                defaults={
                    "amount": amount,
                    "created_by": actor,
                    "updated_by": actor,
                },
            )

        appointment_rows = [
            (
                shop,
                customer_one,
                barber_one,
                now + timedelta(hours=2),
                45,
                Appointment.Status.CONFIRMED,
                Appointment.BookingSource.STAFF,
                Decimal("35.00"),
                manager,
            ),
            (
                shop,
                customer_two,
                barber_two,
                now + timedelta(hours=4),
                30,
                Appointment.Status.REQUESTED,
                Appointment.BookingSource.ONLINE,
                Decimal("28.00"),
                None,
            ),
            (
                shop_two,
                customer_three,
                barber_three,
                now + timedelta(days=1, hours=1),
                60,
                Appointment.Status.CONFIRMED,
                Appointment.BookingSource.PHONE,
                Decimal("40.00"),
                owner_two,
            ),
        ]

        for (
            appointment_shop,
            appointment_customer,
            appointment_barber,
            scheduled_start,
            duration_minutes,
            status,
            booking_source,
            expected_total,
            actor,
        ) in appointment_rows:
            Appointment.objects.get_or_create(
                shop=appointment_shop,
                customer=appointment_customer,
                barber=appointment_barber,
                scheduled_start=scheduled_start,
                defaults={
                    "service_name": "Haircut Session",
                    "duration_minutes": duration_minutes,
                    "status": status,
                    "booking_source": booking_source,
                    "expected_total": expected_total,
                    "notes": "Seeded demo appointment",
                    "created_by": actor,
                    "updated_by": actor,
                },
            )

        self.stdout.write(self.style.SUCCESS("Demo seed data created."))
        self.stdout.write("Demo accounts:")
        self.stdout.write("  platformadmin / ChangeMe12345!")
        self.stdout.write("  owner1 / ChangeMe12345!")
        self.stdout.write("  manager1 / ChangeMe12345!")
        self.stdout.write("  cashier1 / ChangeMe12345!")
        self.stdout.write("  owner2 / ChangeMe12345!")
