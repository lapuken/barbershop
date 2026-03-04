from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("shops", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="shop",
            name="telegram_handle",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="shop",
            name="whatsapp_number",
            field=models.CharField(blank=True, max_length=32),
        ),
    ]
