from rest_framework import serializers

from apps.shops.models import Shop


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = [
            "id",
            "name",
            "branch_code",
            "address",
            "phone",
            "whatsapp_number",
            "telegram_handle",
            "currency",
            "timezone",
            "is_active",
            "created_at",
            "updated_at",
        ]
