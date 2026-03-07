from django.contrib import admin

from apps.sales.models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        "shop",
        "barber",
        "sale_date",
        "total_amount",
        "commission_amount",
        "deleted_at",
    )
    list_filter = ("shop", "sale_date")
    search_fields = ("barber__full_name", "notes")
    inlines = [SaleItemInline]
