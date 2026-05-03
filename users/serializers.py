from rest_framework import serializers
from .models import User, UserBankApp


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "monthly_budget", "language", "is_dark_mode"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
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
        ]
        read_only_fields = ["id"]

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
        return super().update(instance, validated_data)


class SocialAuthSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=["google", "apple"])
    token = serializers.CharField()           # Google: id_token  |  Apple: identity_token
    name = serializers.CharField(required=False, default="")
    email = serializers.EmailField(required=False, default="")


class UserBankAppSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserBankApp
        fields = ["id", "name", "emoji", "store_url", "package_name", "icon_url", "enabled", "created_at"]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
