from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.products.models import Product


class ProductSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        instance = self.instance or Product()
        for attr, value in attrs.items():
            setattr(instance, attr, value)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict or exc.messages)
        return attrs

    class Meta:
        model = Product
        fields = [
            "id",
            "shop",
            "name",
            "sku",
            "category",
            "cost_price",
            "sale_price",
            "is_active",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
