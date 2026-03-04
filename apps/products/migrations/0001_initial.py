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
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("name", models.CharField(max_length=255)),
                ("sku", models.CharField(max_length=64)),
                ("category", models.CharField(max_length=128)),
                ("cost_price", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("sale_price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("is_active", models.BooleanField(default=True)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="product_deleted_records", to="accounts.user")),
                ("shop", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="products", to="shops.shop")),
            ],
            options={"ordering": ["shop__name", "name"]},
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["shop", "is_active", "category"], name="products_pr_shop_id_4bc191_idx"),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["shop", "sku"], name="products_pr_shop_id_8f648a_idx"),
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.UniqueConstraint(condition=models.Q(deleted_at__isnull=True), fields=("shop", "sku"), name="uniq_product_sku_per_shop_active"),
        ),
    ]
