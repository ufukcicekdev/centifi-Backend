from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from expenses.models import Expense, ExpenseList, RecurringExpense
from expenses.recurring_service import compute_next_occurrence, process_due_recurring
from expenses.report_email_copy import category_label, display_list_name, report_email_context, type_label


class RecurringServiceTests(TestCase):
    def test_compute_next_monthly(self):
        d = date(2026, 1, 15)
        n = compute_next_occurrence(d, "monthly")
        self.assertEqual(n, date(2026, 2, 15))

    def test_process_creates_expense(self):
        User = get_user_model()
        u = User.objects.create_user(username="rec@test.com", email="rec@test.com", password="secret12345")
        lst = ExpenseList.objects.create(user=u, name="Private", is_default=True)
        past = timezone.now().date() - timedelta(days=2)
        from decimal import Decimal

        r = RecurringExpense.objects.create(
            user=u,
            expense_list=lst,
            amount=Decimal("25.00"),
            description="Test recurring",
            category="other",
            currency="USD",
            is_income=False,
            recurrence_rule="monthly",
            next_run_at=past,
        )
        stats = process_due_recurring()
        self.assertGreaterEqual(stats["expenses_created"], 1)
        self.assertTrue(Expense.objects.filter(recurring_expense=r).exists())


class ReportEmailCopyTests(TestCase):
    def test_turkish_copy(self):
        ctx = report_email_context(
            lang="tr",
            start=date(2026, 5, 1),
            end=date(2026, 5, 29),
            list_label="Private list",
            count=2,
        )
        self.assertIn("harcama raporu", ctx["subject"].lower())
        self.assertEqual(ctx["col_date"], "Tarih")
        self.assertEqual(category_label("tr", "food"), "Yemek & Restoran")
        self.assertEqual(display_list_name("tr", "Private list"), "Özel liste")
        self.assertEqual(type_label("tr", False), "Harcama")
