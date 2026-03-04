from django.contrib import admin

from apps.barbers.models import Barber


@admin.register(Barber)
class BarberAdmin(admin.ModelAdmin):
    list_display = ("full_name", "shop", "commission_rate", "is_active", "deleted_at")
    list_filter = ("shop", "is_active")
    search_fields = ("full_name", "employee_code", "phone")
