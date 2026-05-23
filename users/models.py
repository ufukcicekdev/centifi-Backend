from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models


class User(AbstractUser):
    monthly_budget = models.DecimalField(max_digits=10, decimal_places=2, default=2000.00)
    language = models.CharField(max_length=5, default="en")
    # ISO 4217 — tercih değişince harcama/tekrar satırlarının currency alanı da buna çekilir (kur dönüşümü yok).
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
    # RevenueCat / mağaza aboneliği — ``pro`` entitlement bitişi (webhook veya /subscription/sync/)
    pro_entitlement_expires_at = models.DateTimeField(null=True, blank=True)

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
    icon_url = models.URLField(max_length=500, blank=True, default="")
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


class PasswordResetOTP(models.Model):
    """Single active row per user after forgot-password; deleted after reset or replacement."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_otps",
    )
    code_hash = models.CharField(max_length=64)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"PasswordResetOTP(user={self.user_id})"


class SiteFeedback(models.Model):
    """Public feedback submitted from centifi.app (and future clients)."""

    class Category(models.TextChoices):
        GENERAL = "general", "General"
        BUG = "bug", "Bug report"
        FEATURE = "feature", "Feature request"
        BILLING = "billing", "Billing / subscription"
        OTHER = "other", "Other"

    name = models.CharField(max_length=120, blank=True, default="")
    email = models.EmailField()
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.GENERAL,
    )
    message = models.TextField()
    language = models.CharField(max_length=5, blank=True, default="en")
    source = models.CharField(max_length=40, default="website")
    user_agent = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "site feedback"
        verbose_name_plural = "site feedback"

    def __str__(self):
        label = (self.name or "").strip() or self.email
        return f"{label} · {self.get_category_display()} · {self.created_at:%Y-%m-%d}"


class TestUserApplication(models.Model):
    """Beta / test user sign-ups from the marketing site."""

    class Platform(models.TextChoices):
        IOS = "ios", "iOS"
        ANDROID = "android", "Android"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        INVITED = "invited", "Invited"
        REJECTED = "rejected", "Rejected"

    email = models.EmailField(unique=True)
    platform = models.CharField(max_length=10, choices=Platform.choices)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    language = models.CharField(max_length=5, blank=True, default="en")
    source = models.CharField(max_length=40, default="website")
    user_agent = models.CharField(max_length=500, blank=True, default="")
    admin_notes = models.TextField(blank=True, default="")
    invited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "test user application"
        verbose_name_plural = "test user applications"

    def __str__(self):
        return f"{self.email} · {self.get_platform_display()} · {self.created_at:%Y-%m-%d}"
