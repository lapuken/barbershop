from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import User, UserShopAccess


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Business Access", {"fields": ("role", "phone", "must_change_password")}),
    )
    list_display = ("username", "email", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")


@admin.register(UserShopAccess)
class UserShopAccessAdmin(admin.ModelAdmin):
    list_display = ("user", "shop", "is_active", "created_at")
    list_filter = ("is_active", "shop")
    search_fields = ("user__username", "shop__name")
