from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.core.models import ShopScopedModel, SoftDeleteModel, TimeStampedModel


class Customer(ShopScopedModel, SoftDeleteModel):
    class ConfirmationChannel(models.TextChoices):
        AUTO = "auto", "Automatic"
        WHATSAPP = "whatsapp", "WhatsApp"
        TELEGRAM = "telegram", "Telegram"

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    telegram_chat_id = models.CharField(max_length=64, blank=True)
    preferred_confirmation_channel = models.CharField(
        max_length=32,
        choices=ConfirmationChannel.choices,
        default=ConfirmationChannel.AUTO,
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["shop__name", "full_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "phone"],
                condition=Q(deleted_at__isnull=True) & ~Q(phone=""),
                name="uniq_customer_phone_per_shop_active",
            ),
            models.UniqueConstraint(
                fields=["shop", "email"],
                condition=Q(deleted_at__isnull=True) & ~Q(email=""),
                name="uniq_customer_email_per_shop_active",
            ),
            models.UniqueConstraint(
                fields=["shop", "telegram_chat_id"],
                condition=Q(deleted_at__isnull=True) & ~Q(telegram_chat_id=""),
                name="uniq_customer_telegram_chat_id_per_shop_active",
            ),
        ]
        indexes = [
            models.Index(fields=["shop", "full_name"]),
            models.Index(fields=["shop", "phone"]),
            models.Index(fields=["shop", "telegram_chat_id"]),
            models.Index(fields=["shop", "is_active"]),
        ]

    def clean(self):
        errors = {}
        if not self.phone and not self.email and not self.telegram_chat_id:
            errors["__all__"] = (
                "Customer needs at least a phone number, email address, or Telegram chat ID."
            )
        if (
            self.preferred_confirmation_channel == self.ConfirmationChannel.WHATSAPP
            and not self.phone
        ):
            errors["phone"] = "A phone number is required for WhatsApp confirmations."
        if (
            self.preferred_confirmation_channel == self.ConfirmationChannel.TELEGRAM
            and not self.telegram_chat_id
        ):
            errors["telegram_chat_id"] = (
                "A Telegram chat ID is required for Telegram confirmations."
            )
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.full_name} ({self.shop.name})"


class Appointment(ShopScopedModel, SoftDeleteModel):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No Show"

    class BookingSource(models.TextChoices):
        ONLINE = "online", "Online"
        PHONE = "phone", "Phone"
        WALK_IN = "walk_in", "Walk-in"
        STAFF = "staff", "Staff"

    ACTIVE_SCHEDULE_STATUSES = {Status.REQUESTED, Status.CONFIRMED}

    customer = models.ForeignKey(
        "appointments.Customer",
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    barber = models.ForeignKey(
        "barbers.Barber",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="appointments",
    )
    service_name = models.CharField(max_length=255)
    scheduled_start = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=45)
    expected_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.CONFIRMED)
    booking_source = models.CharField(
        max_length=32,
        choices=BookingSource.choices,
        default=BookingSource.STAFF,
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="appointments_created",
    )
    updated_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="appointments_updated",
    )

    class Meta:
        ordering = ["scheduled_start", "barber__full_name", "customer__full_name"]
        constraints = [
            models.CheckConstraint(
                check=Q(duration_minutes__gte=15) & Q(duration_minutes__lte=480),
                name="appointment_duration_between_15_480",
            ),
            models.CheckConstraint(
                check=Q(expected_total__gte=0),
                name="appointment_expected_total_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["shop", "scheduled_start"]),
            models.Index(fields=["shop", "status", "scheduled_start"]),
            models.Index(fields=["shop", "barber", "scheduled_start"]),
            models.Index(fields=["customer", "scheduled_start"]),
        ]

    @property
    def scheduled_end(self):
        if not self.scheduled_start:
            return None
        return self.scheduled_start + timedelta(minutes=self.duration_minutes)

    def clean(self):
        errors = {}
        if self.customer_id and self.customer.shop_id != self.shop_id:
            errors["customer"] = "Customer must belong to the selected shop."
        if self.barber_id:
            if self.barber.shop_id != self.shop_id:
                errors["barber"] = "Barber must belong to the selected shop."
            elif not self.barber.is_active or self.barber.deleted_at is not None:
                errors["barber"] = "Inactive barber cannot receive appointments."
        if self.duration_minutes < 15 or self.duration_minutes > 480:
            errors["duration_minutes"] = "Duration must be between 15 and 480 minutes."
        if self.expected_total < Decimal("0.00"):
            errors["expected_total"] = "Expected total must be non-negative."

        if errors:
            raise ValidationError(errors)

        if self.barber_id and self.status in self.ACTIVE_SCHEDULE_STATUSES and self.scheduled_start:
            proposed_end = self.scheduled_end
            overlapping = (
                Appointment.objects.filter(
                    shop_id=self.shop_id,
                    barber_id=self.barber_id,
                    status__in=self.ACTIVE_SCHEDULE_STATUSES,
                )
                .exclude(pk=self.pk)
                .only("scheduled_start", "duration_minutes")
            )
            for existing in overlapping:
                if (
                    existing.scheduled_start < proposed_end
                    and existing.scheduled_end > self.scheduled_start
                ):
                    raise ValidationError(
                        {
                            "scheduled_start": (
                                "This barber already has an overlapping appointment "
                                "in that time window."
                            )
                        }
                    )

    def __str__(self):
        return (
            f"{self.customer.full_name} "
            f"{self.service_name} "
            f"{self.scheduled_start:%Y-%m-%d %H:%M}"
        )


class AppointmentNotification(TimeStampedModel):
    class Channel(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        TELEGRAM = "telegram", "Telegram"

    class EventType(models.TextChoices):
        BOOKING_CONFIRMED = "booking_confirmed", "Booking Confirmed"

    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    customer = models.ForeignKey(
        "appointments.Customer",
        on_delete=models.PROTECT,
        related_name="appointment_notifications",
    )
    shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.PROTECT,
        related_name="appointment_notifications",
    )
    channel = models.CharField(max_length=32, choices=Channel.choices, blank=True)
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    status = models.CharField(max_length=32, choices=Status.choices)
    recipient = models.CharField(max_length=128, blank=True)
    provider_message_id = models.CharField(max_length=128, blank=True)
    provider_response_json = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["appointment", "created_at"]),
            models.Index(fields=["shop", "status", "created_at"]),
            models.Index(fields=["customer", "created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} {self.status} {self.customer.full_name}"
