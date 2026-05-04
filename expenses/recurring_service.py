"""Tekrarlayan masraf: sonraki tarih hesabı ve vadesi gelen kuralların işlenmesi."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils import timezone

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Tek çalıştırmada bir kural için en fazla kaç dönem geri doldurulur (sunucu uzun kapalı kaldıysa)
_MAX_CATCHUP_PER_RULE = 120


def compute_next_occurrence(from_date: date, rule: str) -> date:
    """`from_date` üzerindeki işlemden sonraki bir sonraki takvim günü."""
    if rule == "daily":
        return from_date + timedelta(days=1)
    if rule == "weekly":
        return from_date + timedelta(weeks=1)
    if rule == "biweekly":
        return from_date + timedelta(weeks=2)
    if rule == "monthly":
        return from_date + relativedelta(months=1)
    if rule == "bimonthly":
        return from_date + relativedelta(months=2)
    if rule == "quarterly":
        return from_date + relativedelta(months=3)
    if rule == "yearly":
        return from_date + relativedelta(years=1)
    raise ValueError(f"Unknown recurrence rule: {rule!r}")


def process_due_recurring() -> dict[str, int]:
    """
    `next_run_at <= bugün (timezone-aware gün, USE_TZ ile UTC)` olan aktif kurallar için Expense üretir.

    `select_for_update(skip_locked=True)` ile paralel worker çakışmasını azaltır.
    """
    from .models import Expense, RecurringExpense

    today = timezone.now().date()
    created = 0
    rules_touched = 0

    candidate_ids = list(
        RecurringExpense.objects.filter(is_active=True, next_run_at__lte=today).values_list("pk", flat=True),
    )

    for rid in candidate_ids:
        with transaction.atomic():
            try:
                rule = RecurringExpense.objects.select_for_update(skip_locked=True).get(pk=rid, is_active=True)
            except RecurringExpense.DoesNotExist:
                continue

            n = 0
            while rule.next_run_at <= today and n < _MAX_CATCHUP_PER_RULE:
                Expense.objects.create(
                    user=rule.user,
                    expense_list=rule.expense_list,
                    amount=rule.amount,
                    description=rule.description,
                    category=rule.category,
                    date=rule.next_run_at,
                    currency=rule.currency,
                    is_income=rule.is_income,
                    recurring_expense=rule,
                )
                created += 1
                n += 1
                try:
                    rule.next_run_at = compute_next_occurrence(rule.next_run_at, rule.recurrence_rule)
                except ValueError:
                    logger.warning("Invalid rule %s on recurring %s; disabling.", rule.recurrence_rule, rule.pk)
                    rule.is_active = False
                    break

            rule.save()
            rules_touched += 1

    return {"expenses_created": created, "rules_advanced": rules_touched}
