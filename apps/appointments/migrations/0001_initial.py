import django.db.models.deletion
from decimal import Decimal

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0002_usershopaccess_initial"),
        ("barbers", "0001_initial"),
        ("shops", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Customer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("full_name", models.CharField(max_length=255)),
                ("phone", models.CharField(blank=True, max_length=32)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("notes", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="customer_deleted_records", to=settings.AUTH_USER_MODEL)),
                ("shop", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="customers", to="shops.shop")),
            ],
            options={"ordering": ["shop__name", "full_name"]},
        ),
        migrations.CreateModel(
            name="Appointment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("service_name", models.CharField(max_length=255)),
                ("scheduled_start", models.DateTimeField()),
                ("duration_minutes", models.PositiveIntegerField(default=45)),
                ("expected_total", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("status", models.CharField(choices=[("requested", "Requested"), ("confirmed", "Confirmed"), ("completed", "Completed"), ("cancelled", "Cancelled"), ("no_show", "No Show")], default="confirmed", max_length=32)),
                ("booking_source", models.CharField(choices=[("online", "Online"), ("phone", "Phone"), ("walk_in", "Walk-in"), ("staff", "Staff")], default="staff", max_length=32)),
                ("notes", models.TextField(blank=True)),
                ("barber", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to="barbers.barber")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="appointments_created", to=settings.AUTH_USER_MODEL)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to="appointments.customer")),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="appointment_deleted_records", to=settings.AUTH_USER_MODEL)),
                ("shop", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to="shops.shop")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="appointments_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["scheduled_start", "barber__full_name", "customer__full_name"]},
        ),
        migrations.AddIndex(
            model_name="customer",
            index=models.Index(fields=["shop", "full_name"], name="appointmen_shop_id_36bf62_idx"),
        ),
        migrations.AddIndex(
            model_name="customer",
            index=models.Index(fields=["shop", "phone"], name="appointmen_shop_id_56b323_idx"),
        ),
        migrations.AddIndex(
            model_name="customer",
            index=models.Index(fields=["shop", "is_active"], name="appointmen_shop_id_90b95a_idx"),
        ),
        migrations.AddConstraint(
            model_name="customer",
            constraint=models.UniqueConstraint(
                condition=models.Q(deleted_at__isnull=True) & ~models.Q(phone=""),
                fields=("shop", "phone"),
                name="uniq_customer_phone_per_shop_active",
            ),
        ),
        migrations.AddConstraint(
            model_name="customer",
            constraint=models.UniqueConstraint(
                condition=models.Q(deleted_at__isnull=True) & ~models.Q(email=""),
                fields=("shop", "email"),
                name="uniq_customer_email_per_shop_active",
            ),
        ),
        migrations.AddIndex(
            model_name="appointment",
            index=models.Index(fields=["shop", "scheduled_start"], name="appointmen_shop_id_40f11d_idx"),
        ),
        migrations.AddIndex(
            model_name="appointment",
            index=models.Index(fields=["shop", "status", "scheduled_start"], name="appointmen_shop_id_8cc7b7_idx"),
        ),
        migrations.AddIndex(
            model_name="appointment",
            index=models.Index(fields=["shop", "barber", "scheduled_start"], name="appointmen_shop_id_bf8fe7_idx"),
        ),
        migrations.AddIndex(
            model_name="appointment",
            index=models.Index(fields=["customer", "scheduled_start"], name="appointmen_custome_843bb8_idx"),
        ),
        migrations.AddConstraint(
            model_name="appointment",
            constraint=models.CheckConstraint(
                check=models.Q(duration_minutes__gte=15, duration_minutes__lte=480),
                name="appointment_duration_between_15_480",
            ),
        ),
        migrations.AddConstraint(
            model_name="appointment",
            constraint=models.CheckConstraint(
                check=models.Q(expected_total__gte=0),
                name="appointment_expected_total_non_negative",
            ),
        ),
    ]
