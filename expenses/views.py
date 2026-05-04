import smtplib

from django.db.models import Sum
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Expense, ExpenseList, RecurringExpense, UserCustomCategory
from .report_email import send_expense_report_email
from .serializers import (
    DashboardSerializer,
    ExpenseListSerializer,
    ExpenseSerializer,
    RecurringExpenseSerializer,
    ReportEmailSerializer,
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
        qs = Expense.objects.filter(user=self.request.user).select_related(
            "expense_list",
            "recurring_expense",
        )
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

        recent_expenses = (
            Expense.objects.filter(user=request.user)
            .select_related("expense_list", "recurring_expense")
            .order_by("-date", "-created_at")[:5]
        )

        data = {
            "total_spent": total_spent,
            "monthly_budget": monthly_budget,
            "remaining": monthly_budget - total_spent,
            "category_summary": list(category_summary),
            "recent_expenses": recent_expenses,
        }
        serializer = DashboardSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="send-report-email")
    def send_report_email(self, request):
        ser = ReportEmailSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        start = ser.validated_data["start_date"]
        end = ser.validated_data["end_date"]
        list_id = ser.validated_data.get("list_id")
        try:
            result = send_expense_report_email(
                user=request.user,
                start=start,
                end=end,
                list_id=list_id,
            )
        except ValueError as e:
            return Response(
                {"detail": str(e), "code": "report_email_failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except (smtplib.SMTPException, OSError) as e:
            return Response(
                {"detail": f"Mail server error: {e}", "code": "report_smtp_error"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            return Response(
                {"detail": "Could not send email.", "code": "report_email_error", "reason": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(result, status=status.HTTP_200_OK)


class RecurringExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = RecurringExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return RecurringExpense.objects.filter(user=self.request.user)
