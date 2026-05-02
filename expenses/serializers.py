from rest_framework import serializers

from .models import Category, Expense, ExpenseList, UserCustomCategory

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
        fields = ["id", "name", "is_default"]
        read_only_fields = ["id", "is_default"]

    def update(self, instance, validated_data):
        if instance.is_default and "name" in validated_data:
            raise serializers.ValidationError(
                {"name": "Cannot rename the default list."},
            )
        return super().update(instance, validated_data)


class ExpenseSerializer(serializers.ModelSerializer):
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

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["list_id"] = instance.expense_list_id
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
