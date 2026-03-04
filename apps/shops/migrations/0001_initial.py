from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Shop",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=255)),
                ("branch_code", models.CharField(max_length=32, unique=True)),
                ("address", models.TextField()),
                ("phone", models.CharField(max_length=32)),
                ("currency", models.CharField(default="USD", max_length=8)),
                ("timezone", models.CharField(default="UTC", max_length=64)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddIndex(
            model_name="shop",
            index=models.Index(fields=["branch_code", "is_active"], name="shops_shop_branch__ea97e2_idx"),
        ),
        migrations.AddIndex(
            model_name="shop",
            index=models.Index(fields=["is_active", "name"], name="shops_shop_is_acti_742785_idx"),
        ),
    ]
