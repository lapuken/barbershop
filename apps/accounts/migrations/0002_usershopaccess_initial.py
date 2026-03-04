import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
        ("shops", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserShopAccess",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("shop", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_accesses", to="shops.shop")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="shop_accesses", to="accounts.user")),
            ],
            options={
                "verbose_name": "User Shop Access",
                "verbose_name_plural": "User Shop Access",
                "unique_together": {("user", "shop")},
            },
        ),
        migrations.AddIndex(
            model_name="usershopaccess",
            index=models.Index(fields=["user", "shop", "is_active"], name="accounts_us_user_id_b721d6_idx"),
        ),
    ]
