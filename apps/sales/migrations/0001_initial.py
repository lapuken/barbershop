import django.db.models.deletion
from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
        ("barbers", "0001_initial"),
        ("products", "0001_initial"),
        ("shops", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Sale",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("sale_date", models.DateField()),
                ("total_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("commission_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("notes", models.TextField(blank=True)),
                ("barber", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sales", to="barbers.barber")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sales_created", to="accounts.user")),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sale_deleted_records", to="accounts.user")),
                ("shop", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sales", to="shops.shop")),
                ("updated_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sales_updated", to="accounts.user")),
            ],
            options={"ordering": ["-sale_date", "barber__full_name"]},
        ),
        migrations.CreateModel(
            name="SaleItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("item_type", models.CharField(choices=[("product", "Product"), ("service", "Service")], max_length=16)),
                ("item_name_snapshot", models.CharField(max_length=255)),
                ("unit_price_snapshot", models.DecimalField(decimal_places=2, max_digits=12)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("line_total", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="sale_items", to="products.product")),
                ("sale", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="sales.sale")),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.AddIndex(
            model_name="sale",
            index=models.Index(fields=["shop", "sale_date"], name="sales_sale_shop_id_1f1377_idx"),
        ),
        migrations.AddIndex(
            model_name="sale",
            index=models.Index(fields=["shop", "barber", "sale_date"], name="sales_sale_shop_id_6bdcb7_idx"),
        ),
        migrations.AddConstraint(
            model_name="sale",
            constraint=models.UniqueConstraint(condition=models.Q(deleted_at__isnull=True), fields=("shop", "barber", "sale_date"), name="uniq_sale_per_barber_shop_day_active"),
        ),
    ]
