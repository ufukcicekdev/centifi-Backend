from django.contrib.auth.models import AbstractUser
from django.conf import settings
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


class UserBankApp(models.Model):
    """Bank / wallet apps the user added for notification-based expense hints (synced across devices)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bank_apps",
    )
    name = models.CharField(max_length=120)
    emoji = models.CharField(max_length=16, default="🏦")
    store_url = models.URLField(max_length=500)
    package_name = models.CharField(
        max_length=200,
        help_text="Android applicationId — used to filter notifications.",
    )
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "package_name"],
                name="user_bank_app_unique_package_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.user_id} · {self.name}"
