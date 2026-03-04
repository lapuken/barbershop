from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.appointments.models import Appointment, Customer
from apps.barbers.models import Barber
from apps.shops.models import Shop


class CustomerSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        instance = self.instance or Customer()
        for attr, value in attrs.items():
            setattr(instance, attr, value)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict or exc.messages)
        return attrs

    class Meta:
        model = Customer
        fields = [
            "id",
            "shop",
            "full_name",
            "phone",
            "email",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
            "deleted_at",
        ]


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = [
            "id",
            "shop",
            "customer",
            "barber",
            "service_name",
            "scheduled_start",
            "duration_minutes",
            "expected_total",
            "status",
            "booking_source",
            "notes",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
        read_only_fields = ["created_by", "updated_by", "created_at", "updated_at", "deleted_at"]

    def validate(self, attrs):
        candidate = self.instance or Appointment(
            created_by=self.context["request"].user,
            updated_by=self.context["request"].user,
        )
        for attr, value in attrs.items():
            setattr(candidate, attr, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict or exc.messages)
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        return Appointment.objects.create(**validated_data, created_by=user, updated_by=user)

    def update(self, instance, validated_data):
        user = self.context["request"].user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = user
        instance.full_clean()
        instance.save()
        return instance


class PublicBookingSerializer(serializers.Serializer):
    shop = serializers.PrimaryKeyRelatedField(queryset=Shop.objects.filter(is_active=True))
    customer_name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=32, allow_blank=True, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    barber = serializers.PrimaryKeyRelatedField(
        queryset=Barber.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    service_name = serializers.CharField(max_length=255)
    scheduled_start = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField(min_value=15, max_value=480, default=45)
    notes = serializers.CharField(allow_blank=True, required=False)

    def validate(self, attrs):
        if not attrs.get("phone") and not attrs.get("email"):
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        (
                            "Provide at least a phone number or email address so "
                            "the shop can confirm your booking."
                        )
                    ]
                }
            )
        barber = attrs.get("barber")
        shop = attrs["shop"]
        if barber and barber.shop_id != shop.id:
            raise serializers.ValidationError(
                {"barber": "Selected barber does not belong to the chosen shop."}
            )
        return attrs
