from django.contrib import admin

from apps.products.models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "shop", "sku", "category", "sale_price", "is_active", "deleted_at")
    list_filter = ("shop", "category", "is_active")
    search_fields = ("name", "sku")
