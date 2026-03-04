import django.core.validators
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
            name="Expense",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("expense_date", models.DateField()),
                ("category", models.CharField(max_length=128)),
                ("description", models.TextField()),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("receipt", models.FileField(blank=True, upload_to="receipts/", validators=[django.core.validators.FileExtensionValidator(["pdf", "jpg", "jpeg", "png"])])),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="expenses_created", to="accounts.user")),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="expense_deleted_records", to="accounts.user")),
                ("shop", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="expenses", to="shops.shop")),
                ("updated_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="expenses_updated", to="accounts.user")),
            ],
            options={"ordering": ["-expense_date", "-created_at"]},
        ),
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(fields=["shop", "expense_date"], name="expenses_ex_shop_id_6bac66_idx"),
        ),
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(fields=["shop", "category"], name="expenses_ex_shop_id_c67f37_idx"),
        ),
    ]
