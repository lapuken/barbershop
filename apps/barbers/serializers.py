from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.barbers.models import Barber


class BarberSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        instance = self.instance or Barber()
        for attr, value in attrs.items():
            setattr(instance, attr, value)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict or exc.messages)
        return attrs

    class Meta:
        model = Barber
        fields = [
            "id",
            "shop",
            "full_name",
            "employee_code",
            "phone",
            "commission_rate",
            "is_active",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
