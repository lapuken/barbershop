from django.contrib import admin

from apps.expenses.models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("shop", "expense_date", "category", "amount", "deleted_at")
    list_filter = ("shop", "category", "expense_date")
    search_fields = ("description",)
