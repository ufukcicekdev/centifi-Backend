from django.utils import timezone
from rest_framework import serializers

from .models import Category, Expense, ExpenseList, RecurringExpense, UserCustomCategory
from .recurring_service import compute_next_occurrence

BUILTIN_CATEGORY_VALUES = frozenset(c.value for c in Category)


class UserCustomCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCustomCategory
        fields = ["id", "name", "emoji", "color", "bg_color", "created_at"]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class ExpenseListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseList
        fields = ["id", "name", "is_default", "emoji"]
        read_only_fields = ["id", "is_default"]

    def update(self, instance, validated_data):
        if instance.is_default:
            errs = {}
            if "name" in validated_data:
                errs["name"] = "Cannot rename the default list."
            if "emoji" in validated_data:
                errs["emoji"] = "Cannot change the default list icon."
            if errs:
                raise serializers.ValidationError(errs)
        return super().update(instance, validated_data)


class ExpenseSerializer(serializers.ModelSerializer):
    """
    OPTIMIZED: Caches user's custom categories on init to prevent N+1 queries
    """
    list_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Expense
        fields = [
            "id",
            "amount",
            "description",
            "category",
            "date",
            "currency",
            "is_income",
            "receipt_url",
            "created_at",
            "updated_at",
            "list_id",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ✅ FIX_02: Cache user's custom categories on serializer init
        # This prevents N+1 queries when validating multiple expenses
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            # Fetch all custom category IDs once per request
            self._user_custom_category_ids = set(
                UserCustomCategory.objects.filter(user=request.user).values_list("pk", flat=True)
            )
        else:
            self._user_custom_category_ids = set()

    def validate_category(self, value):
        """
        Validate category is either builtin or user's custom category.
        Uses in-memory check (no DB hit) thanks to cached IDs.
        """
        if value in BUILTIN_CATEGORY_VALUES:
            return value
        if isinstance(value, str) and value.startswith("custom_"):
            suffix = value[7:]
            if suffix.isdigit():
                pk = int(suffix)
                # ✅ IN-MEMORY CHECK (from cache, no DB query)
                if pk in self._user_custom_category_ids:
                    return value
        raise serializers.ValidationError("Invalid category.")

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["list_id"] = instance.expense_list_id
        ret["recurring_expense_id"] = instance.recurring_expense_id
        rel = getattr(instance, "recurring_expense", None)
        ret["recurrence_rule"] = rel.recurrence_rule if rel else None
        return ret

    def _resolve_expense_list(self, user, list_id):
        if list_id is None:
            return ExpenseList.objects.filter(user=user, is_default=True).first()
        try:
            return ExpenseList.objects.get(pk=list_id, user=user)
        except ExpenseList.DoesNotExist as exc:
            raise serializers.ValidationError({"list_id": "Invalid list for this user."}) from exc

    def create(self, validated_data):
        list_id = validated_data.pop("list_id", None)
        user = self.context["request"].user
        validated_data["user"] = user
        validated_data["expense_list"] = self._resolve_expense_list(user, list_id)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        list_id = validated_data.pop("list_id", serializers.empty)
        if list_id is not serializers.empty:
            user = self.context["request"].user
            validated_data["expense_list"] = self._resolve_expense_list(user, list_id)
        return super().update(instance, validated_data)


class MonthlySummarySerializer(serializers.Serializer):
    category = serializers.CharField()
    total = serializers.DecimalField(max_digits=10, decimal_places=2)


class DashboardSerializer(serializers.Serializer):
    total_spent = serializers.DecimalField(max_digits=10, decimal_places=2)
    monthly_budget = serializers.DecimalField(max_digits=10, decimal_places=2)
    remaining = serializers.DecimalField(max_digits=10, decimal_places=2)
    category_summary = MonthlySummarySerializer(many=True)
    recent_expenses = ExpenseSerializer(many=True)


class RecurringExpenseSerializer(serializers.ModelSerializer):
    """İlk `anchor_date` gelecekteyse Expense yok; vade gelince arka plan işler."""

    list_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    anchor_date = serializers.DateField(write_only=True, required=False)
    initial_expense = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RecurringExpense
        fields = [
            "id",
            "series_id",
            "amount",
            "description",
            "category",
            "currency",
            "is_income",
            "recurrence_rule",
            "next_run_at",
            "is_active",
            "created_at",
            "updated_at",
            "list_id",
            "anchor_date",
            "initial_expense",
        ]
        read_only_fields = ["id", "series_id", "next_run_at", "initial_expense", "created_at", "updated_at"]

    def validate(self, attrs):
        if self.instance is None and not attrs.get("anchor_date"):
            raise serializers.ValidationError({"anchor_date": "This field is required when creating a rule."})
        return attrs

    def get_initial_expense(self, obj: RecurringExpense):
        first = Expense.objects.filter(recurring_expense=obj).order_by("date", "id").first()
        if not first:
            return None
        return ExpenseSerializer(first, context=self.context).data

    def validate_category(self, value):
        user = self.context["request"].user
        if value in BUILTIN_CATEGORY_VALUES:
            return value
        if isinstance(value, str) and value.startswith("custom_"):
            suffix = value[7:]
            if suffix.isdigit():
                pk = int(suffix)
                if UserCustomCategory.objects.filter(pk=pk, user=user).exists():
                    return value
        raise serializers.ValidationError("Invalid category.")

    def _resolve_expense_list(self, user, list_id):
        if list_id is None:
            return ExpenseList.objects.filter(user=user, is_default=True).first()
        try:
            return ExpenseList.objects.get(pk=list_id, user=user)
        except ExpenseList.DoesNotExist as exc:
            raise serializers.ValidationError({"list_id": "Invalid list for this user."}) from exc

    def create(self, validated_data):
        list_id = validated_data.pop("list_id", None)
        anchor = validated_data.pop("anchor_date")
        user = self.context["request"].user
        validated_data["user"] = user
        validated_data["expense_list"] = self._resolve_expense_list(user, list_id)
        validated_data["next_run_at"] = anchor
        rule = RecurringExpense.objects.create(**validated_data)

        today = timezone.now().date()
        if anchor <= today:
            Expense.objects.create(
                user=user,
                expense_list=rule.expense_list,
                amount=rule.amount,
                description=rule.description,
                category=rule.category,
                date=anchor,
                currency=rule.currency,
                is_income=rule.is_income,
                recurring_expense=rule,
            )
            rule.next_run_at = compute_next_occurrence(anchor, rule.recurrence_rule)
            rule.save(update_fields=["next_run_at", "updated_at"])
        return rule

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["list_id"] = instance.expense_list_id
        return ret


class ReportEmailSerializer(serializers.Serializer):
    """POST /api/expenses/send-report-email/ — CSV attachment to the signed-in user's email."""

    start_date = serializers.DateField()
    end_date = serializers.DateField()
    list_id = serializers.IntegerField(required=False, allow_null=True)
    language = serializers.CharField(required=False, allow_blank=True, max_length=5)

    def validate_language(self, value: str) -> str:
        from users.password_email_copy import normalize_email_language

        raw = (value or "").strip()
        if not raw:
            return ""
        return normalize_email_language(raw)

    def validate(self, attrs):
        start = attrs["start_date"]
        end = attrs["end_date"]
        if end < start:
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after start date."},
            )
        if (end - start).days > 366:
            raise serializers.ValidationError(
                {"end_date": "Date range cannot exceed 366 days."},
            )
        return attrs
