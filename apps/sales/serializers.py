from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.sales.models import Sale, SaleItem
from apps.sales.services import duplicate_sale_for, save_sale_with_items


class SaleItemSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        product = attrs.get("product")
        item_type = attrs.get("item_type")
        if item_type == SaleItem.PRODUCT:
            if not product:
                raise serializers.ValidationError(
                    {"product": "Product is required for product sale items."}
                )
            if not product.is_active or product.deleted_at is not None:
                raise serializers.ValidationError(
                    {"product": "Inactive product cannot be used in new sales."}
                )
        if item_type == SaleItem.SERVICE:
            if not attrs.get("item_name_snapshot"):
                raise serializers.ValidationError(
                    {"item_name_snapshot": "Service name is required."}
                )
            if attrs.get("unit_price_snapshot") is None:
                raise serializers.ValidationError(
                    {"unit_price_snapshot": "Unit price is required."}
                )
        return attrs

    class Meta:
        model = SaleItem
        fields = [
            "id",
            "item_type",
            "product",
            "item_name_snapshot",
            "unit_price_snapshot",
            "quantity",
            "line_total",
        ]
        read_only_fields = ["line_total"]
        extra_kwargs = {
            "product": {"required": False, "allow_null": True},
            "item_name_snapshot": {"required": False, "allow_blank": True},
            "unit_price_snapshot": {"required": False},
        }


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)

    class Meta:
        model = Sale
        fields = [
            "id",
            "shop",
            "barber",
            "sale_date",
            "total_amount",
            "commission_amount",
            "notes",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "deleted_at",
            "items",
        ]
        read_only_fields = [
            "total_amount",
            "commission_amount",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "deleted_at",
        ]

    def validate(self, attrs):
        shop = attrs.get("shop", getattr(self.instance, "shop", None))
        barber = attrs.get("barber", getattr(self.instance, "barber", None))
        sale_date = attrs.get("sale_date", getattr(self.instance, "sale_date", None))
        existing = duplicate_sale_for(
            shop, barber, sale_date, exclude_sale_id=getattr(self.instance, "pk", None)
        )
        if existing:
            raise serializers.ValidationError(
                {"non_field_errors": ["Daily sale already exists for this barber and shop/date."]}
            )
        candidate = self.instance or Sale(
            created_by=self.context["request"].user, updated_by=self.context["request"].user
        )
        for attr, value in attrs.items():
            if attr == "items":
                continue
            setattr(candidate, attr, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict or exc.messages)
        return attrs

    def create(self, validated_data):
        items = validated_data.pop("items", [])
        user = self.context["request"].user
        sale = Sale(**validated_data, created_by=user, updated_by=user)
        save_sale_with_items(sale=sale, items_data=items, user=user)
        return sale

    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        user = self.context["request"].user
        if items is None:
            items = [
                {
                    "item_type": item.item_type,
                    "product": item.product,
                    "item_name_snapshot": item.item_name_snapshot,
                    "unit_price_snapshot": item.unit_price_snapshot,
                    "quantity": item.quantity,
                }
                for item in instance.items.all()
            ]
        save_sale_with_items(sale=instance, items_data=items, user=user)
        return instance
