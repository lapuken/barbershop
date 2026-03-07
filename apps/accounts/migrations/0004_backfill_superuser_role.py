from django.db import migrations


def set_superusers_to_platform_admin(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(is_superuser=True).exclude(role="platform_admin").update(role="platform_admin")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_rename_accounts_us_user_id_b721d6_idx_accounts_us_user_id_45e0ba_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(set_superusers_to_platform_admin, migrations.RunPython.noop),
    ]
