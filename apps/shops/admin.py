from django.contrib import admin

from apps.shops.models import Shop


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("name", "branch_code", "currency", "timezone", "is_active")
    list_filter = ("is_active", "currency")
    search_fields = ("name", "branch_code", "phone")
