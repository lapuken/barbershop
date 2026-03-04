import django.db.models.deletion

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("appointments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="preferred_confirmation_channel",
            field=models.CharField(
                choices=[
                    ("auto", "Automatic"),
                    ("whatsapp", "WhatsApp"),
                    ("telegram", "Telegram"),
                ],
                default="auto",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="customer",
            name="telegram_chat_id",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddIndex(
            model_name="customer",
            index=models.Index(fields=["shop", "telegram_chat_id"], name="appointmen_shop_id_9d14d0_idx"),
        ),
        migrations.AddConstraint(
            model_name="customer",
            constraint=models.UniqueConstraint(
                condition=models.Q(deleted_at__isnull=True) & ~models.Q(telegram_chat_id=""),
                fields=("shop", "telegram_chat_id"),
                name="uniq_customer_telegram_chat_id_per_shop_active",
            ),
        ),
        migrations.CreateModel(
            name="AppointmentNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("channel", models.CharField(blank=True, choices=[("whatsapp", "WhatsApp"), ("telegram", "Telegram")], max_length=32)),
                ("event_type", models.CharField(choices=[("booking_confirmed", "Booking Confirmed")], max_length=32)),
                ("status", models.CharField(choices=[("sent", "Sent"), ("failed", "Failed"), ("skipped", "Skipped")], max_length=32)),
                ("recipient", models.CharField(blank=True, max_length=128)),
                ("provider_message_id", models.CharField(blank=True, max_length=128)),
                ("provider_response_json", models.JSONField(blank=True, default=dict)),
                ("error_message", models.TextField(blank=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("appointment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="appointments.appointment")),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="appointment_notifications", to="appointments.customer")),
                ("shop", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="appointment_notifications", to="shops.shop")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="appointmentnotification",
            index=models.Index(fields=["appointment", "created_at"], name="appointmen_appoint_748f98_idx"),
        ),
        migrations.AddIndex(
            model_name="appointmentnotification",
            index=models.Index(fields=["shop", "status", "created_at"], name="appointmen_shop_id_befbca_idx"),
        ),
        migrations.AddIndex(
            model_name="appointmentnotification",
            index=models.Index(fields=["customer", "created_at"], name="appointmen_custome_3d7650_idx"),
        ),
    ]
