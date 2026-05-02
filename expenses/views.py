from django.db.models import Sum
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Expense, ExpenseList, UserCustomCategory
from .serializers import (
    DashboardSerializer,
    ExpenseListSerializer,
    ExpenseSerializer,
    UserCustomCategorySerializer,
)


class UserCustomCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = UserCustomCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return UserCustomCategory.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        slug = instance.slug
        Expense.objects.filter(user=self.request.user, category=slug).update(category=Category.OTHER)
        super().perform_destroy(instance)


class ExpenseListViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ExpenseList.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, is_default=False)

    def perform_destroy(self, instance):
        if instance.is_default:
            raise PermissionDenied("Cannot delete the default list.")
        super().perform_destroy(instance)


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Expense.objects.filter(user=self.request.user)
        # Optional filters: ?month=2026-05  ?category=food
        month = self.request.query_params.get("month")
        category = self.request.query_params.get("category")
        if month:
            year, m = month.split("-")
            qs = qs.filter(date__year=year, date__month=m)
        if category:
            qs = qs.filter(category=category)
        return qs

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        now = timezone.now()
        monthly_qs = Expense.objects.filter(
            user=request.user,
            date__year=now.year,
            date__month=now.month,
        )

        total_spent = monthly_qs.aggregate(t=Sum("amount"))["t"] or 0
        monthly_budget = request.user.monthly_budget

        category_summary = (
            monthly_qs.values("category")
            .annotate(total=Sum("amount"))
            .order_by("-total")[:3]
        )

        recent_expenses = Expense.objects.filter(user=request.user)[:5]

        data = {
            "total_spent": total_spent,
            "monthly_budget": monthly_budget,
            "remaining": monthly_budget - total_spent,
            "category_summary": list(category_summary),
            "recent_expenses": recent_expenses,
        }
        serializer = DashboardSerializer(data)
        return Response(serializer.data)
