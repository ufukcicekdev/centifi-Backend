from django.contrib import admin

from .models import Expense, RecurringExpense


@admin.register(RecurringExpense)
class RecurringExpenseAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "recurrence_rule", "next_run_at", "is_active", "amount", "description")
    list_filter = ("is_active", "recurrence_rule")
    raw_id_fields = ("user", "expense_list")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "date", "amount", "description", "recurring_expense")
    raw_id_fields = ("user", "expense_list", "recurring_expense")
