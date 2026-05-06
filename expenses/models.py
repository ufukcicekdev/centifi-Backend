import uuid

from django.conf import settings
from django.db import models


class Category(models.TextChoices):
    FOOD = "food", "Food & Dining"
    TRANSPORT = "transport", "Transport"
    SHOPPING = "shopping", "Shopping"
    HEALTH = "health", "Health"
    ENTERTAINMENT = "entertainment", "Entertainment"
    UTILITIES = "utilities", "Utilities"
    OTHER = "other", "Other"


class ExpenseList(models.Model):
    """User-defined expense lists (e.g. Private, Trip, Shared)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="expense_lists",
    )
    name = models.CharField(max_length=120)
    is_default = models.BooleanField(default=False)
    emoji = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        ordering = ["-is_default", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="expense_list_one_default_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.user_id} · {self.name}"


class UserCustomCategory(models.Model):
    """User-defined category; referenced by Expense.category as custom_<id>."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="custom_categories",
    )
    name = models.CharField(max_length=80)
    emoji = models.CharField(max_length=16, default="📦")
    color = models.CharField(max_length=20, default="#A29BFE")
    bg_color = models.CharField(max_length=24, default="#A29BFE20")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.user_id} · {self.name}"

    @property
    def slug(self) -> str:
        return f"custom_{self.pk}"


class Expense(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="expenses",
    )
    expense_list = models.ForeignKey(
        ExpenseList,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    category = models.CharField(max_length=48, default=Category.OTHER)
    date = models.DateField()
    currency = models.CharField(max_length=5, default="USD")
    is_income = models.BooleanField(default=False)
    receipt_url = models.URLField(blank=True, default="")
    recurring_expense = models.ForeignKey(
        "expenses.RecurringExpense",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_expenses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.description} ({self.amount})"


class RecurringExpense(models.Model):
    """Kullanıcı tanımlı tekrar; Celery/cron `process_due_recurring` ile Expense üretir."""

    class Recurrence(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        BIWEEKLY = "biweekly", "Biweekly"
        MONTHLY = "monthly", "Monthly"
        BIMONTHLY = "bimonthly", "Bimonthly"
        QUARTERLY = "quarterly", "Quarterly"
        YEARLY = "yearly", "Yearly"

    series_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recurring_expenses",
    )
    expense_list = models.ForeignKey(
        ExpenseList,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurring_templates",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    category = models.CharField(max_length=48, default=Category.OTHER)
    currency = models.CharField(max_length=5, default="USD")
    is_income = models.BooleanField(default=False)
    recurrence_rule = models.CharField(max_length=16, choices=Recurrence.choices)
    next_run_at = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id} · {self.recurrence_rule} · {self.description[:40]}"
