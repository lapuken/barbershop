import copy

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.appointments.models import Appointment, Customer
from apps.appointments.notifications import send_booking_confirmation
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
            "telegram_chat_id",
            "preferred_confirmation_channel",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
        validators = []


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
        candidate = (
            copy.deepcopy(self.instance)
            if self.instance
            else Appointment(
                created_by=self.context["request"].user,
                updated_by=self.context["request"].user,
            )
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
        appointment = Appointment.objects.create(**validated_data, created_by=user, updated_by=user)
        if appointment.status == Appointment.Status.CONFIRMED:
            send_booking_confirmation(appointment, request=self.context.get("request"))
        return appointment

    def update(self, instance, validated_data):
        user = self.context["request"].user
        previous_status = instance.status
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = user
        instance.full_clean()
        instance.save()
        if previous_status != Appointment.Status.CONFIRMED and instance.status == Appointment.Status.CONFIRMED:
            send_booking_confirmation(instance, request=self.context.get("request"))
        return instance


class PublicBookingSerializer(serializers.Serializer):
    shop = serializers.PrimaryKeyRelatedField(queryset=Shop.objects.filter(is_active=True))
    customer_name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=32, allow_blank=True, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    telegram_chat_id = serializers.CharField(max_length=64, allow_blank=True, required=False)
    preferred_confirmation_channel = serializers.ChoiceField(
        choices=Customer.ConfirmationChannel.choices,
        required=False,
        default=Customer.ConfirmationChannel.AUTO,
    )
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
        if not attrs.get("phone") and not attrs.get("email") and not attrs.get("telegram_chat_id"):
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        (
                            "Provide at least a phone number, email address, or Telegram chat ID "
                            "so the shop can confirm your booking."
                        )
                    ]
                }
            )
        preferred_channel = attrs.get(
            "preferred_confirmation_channel",
            Customer.ConfirmationChannel.AUTO,
        )
        if preferred_channel == Customer.ConfirmationChannel.WHATSAPP and not attrs.get("phone"):
            raise serializers.ValidationError(
                {"phone": ["A phone number is required for WhatsApp confirmations."]}
            )
        if (
            preferred_channel == Customer.ConfirmationChannel.TELEGRAM
            and not attrs.get("telegram_chat_id")
        ):
            raise serializers.ValidationError(
                {"telegram_chat_id": ["A Telegram chat ID is required for Telegram confirmations."]}
            )
        barber = attrs.get("barber")
        shop = attrs["shop"]
        if barber and barber.shop_id != shop.id:
            raise serializers.ValidationError(
                {"barber": "Selected barber does not belong to the chosen shop."}
            )
        return attrs
