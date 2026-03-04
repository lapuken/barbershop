from django.contrib import admin

from apps.appointments.models import Appointment, Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "shop", "phone", "email", "is_active", "deleted_at")
    list_filter = ("shop", "is_active")
    search_fields = ("full_name", "phone", "email")


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
