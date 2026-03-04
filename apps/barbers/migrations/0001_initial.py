import django.db.models.deletion
from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
        ("shops", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Barber",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("full_name", models.CharField(max_length=255)),
                ("employee_code", models.CharField(blank=True, max_length=64)),
                ("phone", models.CharField(blank=True, max_length=32)),
                ("commission_rate", models.DecimalField(decimal_places=2, default=Decimal("50.00"), max_digits=5)),
                ("is_active", models.BooleanField(default=True)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="barber_deleted_records", to="accounts.user")),
                ("shop", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="barbers", to="shops.shop")),
            ],
            options={"ordering": ["shop__name", "full_name"]},
        ),
        migrations.AddIndex(
            model_name="barber",
            index=models.Index(fields=["shop", "is_active", "full_name"], name="barbers_bar_shop_id_8f51d4_idx"),
        ),
        migrations.AddConstraint(
            model_name="barber",
            constraint=models.UniqueConstraint(condition=models.Q(deleted_at__isnull=True), fields=("shop", "full_name"), name="uniq_barber_name_per_shop_active"),
        ),
        migrations.AddConstraint(
            model_name="barber",
            constraint=models.UniqueConstraint(condition=models.Q(deleted_at__isnull=True) & ~models.Q(employee_code=""), fields=("shop", "employee_code"), name="uniq_barber_employee_per_shop_active"),
        ),
        migrations.AddConstraint(
            model_name="barber",
            constraint=models.CheckConstraint(check=models.Q(commission_rate__gte=0, commission_rate__lte=100), name="barber_commission_between_0_100"),
        ),
    ]
