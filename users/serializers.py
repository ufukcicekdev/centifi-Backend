from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from expenses.models import Expense, RecurringExpense

from .models import User, UserBankApp


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "monthly_budget", "language", "is_dark_mode"]

    def validate_email(self, value):
        if not value:
            return value
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email, deleted_at__isnull=False).exists():
            raise serializers.ValidationError(
                "This email belongs to a deleted account and cannot be reused."
            )
        return email

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyPasswordResetCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.RegexField(r"^\d{6}$")


class ResetPasswordSerializer(serializers.Serializer):
    reset_token = serializers.CharField()
    new_password = serializers.CharField(min_length=6, write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=False, default="", allow_blank=True, write_only=True)
    new_password = serializers.CharField(min_length=6, write_only=True)


class UserSerializer(serializers.ModelSerializer):
    is_pro = serializers.SerializerMethodField()
    has_password = serializers.SerializerMethodField()

    def get_has_password(self, obj: User) -> bool:
        return obj.has_usable_password()

    def get_is_pro(self, obj: User) -> bool:
        exp = obj.pro_entitlement_expires_at
        if exp is None:
            return False
        return exp > timezone.now()

    def validate_email(self, value):
        if value is None or (isinstance(value, str) and not value.strip()):
            raise serializers.ValidationError("This field may not be blank.")
        v = value.strip().lower()
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            if User.objects.exclude(pk=user.pk).filter(email__iexact=v).exists():
                raise serializers.ValidationError("A user with this email already exists.")
        return v

    def validate_budget_alert_threshold_percent(self, value):
        if value is None:
            return value
        v = int(value)
        if v < 50 or v > 100:
            raise serializers.ValidationError("Must be between 50 and 100.")
        return v

    def validate_display_currency(self, value):
        if value is None or value == "":
            return value
        v = str(value).strip().upper()
        if len(v) != 3 or not v.isalpha():
            raise serializers.ValidationError("Must be a 3-letter ISO 4217 code.")
        return v

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "monthly_budget", "language", "display_currency", "is_dark_mode", "notifications_enabled",
            "alert_email", "onboarding_completed",
            "category_budgets", "budget_alerts_enabled", "budget_alert_threshold_percent",
            "pro_entitlement_expires_at", "is_pro", "has_password",
            "trial_started_at",
        ]
        read_only_fields = ["id", "pro_entitlement_expires_at", "is_pro", "has_password", "trial_started_at"]

    def update(self, instance, validated_data):
        email = validated_data.get("email")
        if email is not None:
            ne = email.strip().lower()
            validated_data["email"] = ne
            # Registration uses email as username; keep login identifier aligned
            if instance.email and instance.username.lower() == instance.email.lower():
                validated_data["username"] = ne
        for key in ("first_name", "last_name"):
            if key in validated_data and isinstance(validated_data[key], str):
                validated_data[key] = validated_data[key].strip()
        prev_display_currency = instance.display_currency
        with transaction.atomic():
            updated = super().update(instance, validated_data)
            new_dc = updated.display_currency
            if new_dc != prev_display_currency:
                Expense.objects.filter(user=updated).update(currency=new_dc)
                RecurringExpense.objects.filter(user=updated).update(currency=new_dc)
        return updated


class SocialAuthSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=["google", "apple"])
    token = serializers.CharField(trim_whitespace=True)
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True, default="")
    email = serializers.CharField(required=False, allow_blank=True, allow_null=True, default="")
    language = serializers.CharField(required=False, allow_blank=True, allow_null=True, default="", max_length=5)

    def validate_token(self, value: str) -> str:
        token = (value or "").strip()
        if not token:
            raise serializers.ValidationError("Token is required.")
        return token

    def validate_email(self, value: str | None) -> str:
        from django.core.exceptions import ValidationError as DjangoValidationError
        from django.core.validators import validate_email as django_validate_email

        raw = (value or "").strip()
        if not raw:
            return ""
        try:
            django_validate_email(raw)
        except DjangoValidationError:
            return ""
        return raw

    def validate_language(self, value: str | None) -> str:
        from users.password_email_copy import normalize_email_language

        raw = (value or "").strip()
        if not raw:
            return ""
        return normalize_email_language(raw)


class UserBankAppSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserBankApp
        fields = ["id", "name", "emoji", "store_url", "package_name", "icon_url", "enabled", "created_at"]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
