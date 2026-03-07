from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.expenses.models import Expense


class ExpenseSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        instance = self.instance or Expense(
            created_by=self.context["request"].user, updated_by=self.context["request"].user
        )
        for attr, value in attrs.items():
            setattr(instance, attr, value)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict or exc.messages)
        return attrs

    class Meta:
        model = Expense
        fields = [
            "id",
            "shop",
            "expense_date",
            "category",
            "description",
            "amount",
            "receipt",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
        read_only_fields = ["created_by", "updated_by", "created_at", "updated_at", "deleted_at"]
