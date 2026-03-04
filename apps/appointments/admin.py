from django.contrib import admin

from apps.appointments.models import Appointment, AppointmentNotification, Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "shop",
        "phone",
        "telegram_chat_id",
        "preferred_confirmation_channel",
        "is_active",
        "deleted_at",
    )
    list_filter = ("shop", "is_active")
    search_fields = ("full_name", "phone", "email", "telegram_chat_id")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "service_name",
        "shop",
        "customer",
        "barber",
        "scheduled_start",
        "status",
        "booking_source",
    )
    list_filter = ("shop", "status", "booking_source")
    search_fields = ("service_name", "customer__full_name", "customer__phone")


@admin.register(AppointmentNotification)
class AppointmentNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "appointment",
        "channel",
        "event_type",
        "status",
        "recipient",
        "sent_at",
        "created_at",
    )
    list_filter = ("shop", "channel", "event_type", "status")
    search_fields = ("customer__full_name", "recipient", "provider_message_id")
