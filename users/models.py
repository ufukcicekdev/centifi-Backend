from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    monthly_budget = models.DecimalField(max_digits=10, decimal_places=2, default=2000.00)
    language = models.CharField(max_length=5, default="en")
    # ISO 4217 — UI formatting / budget display (not expense transaction currency)
    display_currency = models.CharField(max_length=3, default="USD")
    is_dark_mode = models.BooleanField(default=True)
    notifications_enabled = models.BooleanField(default=True)
    alert_email = models.EmailField(blank=True, default="")
    onboarding_completed = models.BooleanField(default=False)
    # Per-category monthly budgets + alert prefs (JSON: { "food": { "amount": 200, "budgetColor": "#..." }, ... })
    category_budgets = models.JSONField(default=dict, blank=True)
    budget_alerts_enabled = models.BooleanField(default=True)
    budget_alert_threshold_percent = models.PositiveSmallIntegerField(default=90)
    # Social auth provider IDs
    google_id = models.CharField(max_length=255, blank=True, default="")
    apple_id = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return self.username
