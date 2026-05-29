"""Expense report email: HTML table in body + CSV attachment (SMTP2GO / any SMTP)."""

import csv
import io
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from core.email_branding import attach_centifi_logo_inline_if_needed, wrap_branded_email_html

from .models import Expense, ExpenseList
from users.password_email_copy import normalize_email_language

from .report_email_copy import (
    category_label,
    display_list_name,
    report_email_context,
    type_label,
)

User = get_user_model()


def _smtp_ready() -> bool:
    backend = (getattr(settings, "EMAIL_BACKEND", "") or "").lower()
    if "console" in backend or "locmem" in backend or "dummy" in backend:
        return True
    if getattr(settings, "SMTP2GO_API_KEY", "").strip() and getattr(settings, "SMTP2GO_FROM_EMAIL", "").strip():
        return True
    return bool(
        getattr(settings, "EMAIL_HOST", "").strip()
        and getattr(settings, "DEFAULT_FROM_EMAIL", "").strip(),
    )


def _expense_queryset(user: User, start: date, end: date, list_id: int | None):
    qs = Expense.objects.filter(user=user, date__gte=start, date__lte=end).select_related(
        "expense_list",
    )
    if list_id is not None:
        qs = qs.filter(expense_list_id=list_id)
    return qs.order_by("date", "id")


def _rows(user: User, start: date, end: date, list_id: int | None) -> list[dict]:
    out: list[dict] = []
    for e in _expense_queryset(user, start, end, list_id):
        list_name = ""
        if e.expense_list_id and e.expense_list:
            list_name = e.expense_list.name
        out.append(
            {
                "date": e.date.isoformat(),
                "amount": e.amount,
                "currency": e.currency,
                "category": e.category,
                "description": e.description.replace("\n", " ").replace("\r", ""),
                "list": list_name,
                "is_income": e.is_income,
            },
        )
    return out


def _localize_rows_for_email(lang: str, rows: list[dict]) -> list[dict]:
    localized: list[dict] = []
    for r in rows:
        localized.append(
            {
                **r,
                "category": category_label(lang, r["category"]),
                "list": display_list_name(lang, r["list"]),
                "type_label": type_label(lang, r["is_income"]),
            },
        )
    return localized


def _build_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        ["date", "amount", "currency", "category", "description", "list", "is_income"],
    )
    for r in rows:
        w.writerow(
            [
                r["date"],
                f"{r['amount']:.2f}",
                r["currency"],
                r["category"],
                r["description"],
                r["list"],
                "1" if r["is_income"] else "0",
            ],
        )
    return buf.getvalue()


def _render_report_inner_html(
    rows: list[dict],
    *,
    ctx: dict,
    list_label: str,
) -> str:
    """Intro + table from ``email_templates/reports/expense_report.html``."""
    return render_to_string(
        "reports/expense_report.html",
        {
            "rows": rows,
            "period": ctx["period"],
            "list_label": display_list_name(ctx["html_lang"], list_label) if list_label else "",
            "greeting": ctx["greeting"],
            "intro_prefix": ctx["intro_prefix"],
            "intro_suffix": ctx["intro_suffix"],
            "empty_message": ctx["empty_message"],
            "col_date": ctx["col_date"],
            "col_amount": ctx["col_amount"],
            "col_category": ctx["col_category"],
            "col_description": ctx["col_description"],
            "col_list": ctx["col_list"],
            "col_type": ctx["col_type"],
        },
    )


def send_expense_report_email(
    *,
    user: User,
    start: date,
    end: date,
    list_id: int | None = None,
    language: str | None = None,
) -> dict:
    """
    Sends multipart email: HTML body (table) + plain-text fallback + CSV attachment.
    Copy follows request ``language`` (app UI) or ``user.language`` (en, tr, de, fr, es).
    """
    if not user.email or not str(user.email).strip():
        raise ValueError("Your account has no email address.")

    if not _smtp_ready():
        raise ValueError(
            "Email delivery is not configured on the server. "
            "Set SMTP2GO_API_KEY and SMTP2GO_FROM_EMAIL (REST API), or "
            "EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL for SMTP.",
        )

    list_label = ""
    if list_id is not None:
        if not ExpenseList.objects.filter(pk=list_id, user=user).exists():
            raise ValueError("Invalid list for this account.")
        el = ExpenseList.objects.get(pk=list_id, user=user)
        list_label = el.name

    lang = normalize_email_language(language or getattr(user, "language", None) or "en")
    if language and lang != normalize_email_language(getattr(user, "language", None) or ""):
        user.language = lang
        user.save(update_fields=["language"])
    rows_raw = _rows(user, start, end, list_id)
    count = len(rows_raw)
    csv_text = _build_csv(rows_raw)
    rows_display = _localize_rows_for_email(lang, rows_raw)

    ctx = report_email_context(
        lang=lang,
        start=start,
        end=end,
        list_label=list_label,
        count=count,
    )

    subject = ctx["subject"]
    inner_html = _render_report_inner_html(rows_display, ctx=ctx, list_label=list_label)
    html_body = wrap_branded_email_html(
        inner_html=inner_html,
        document_title=subject,
        header_subtitle=ctx["header_subtitle"],
        preheader=ctx["preheader"],
        html_lang=ctx["html_lang"],
        footer_sent_by=ctx["footer_sent_by"],
        footer_tagline=ctx["footer_tagline"],
    )

    text_body = ctx["plain_body"]

    filename = f"centifi-expenses-{start.isoformat()}-to-{end.isoformat()}.csv"

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email.strip()],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.attach(filename, csv_text.encode("utf-8"), "text/csv; charset=utf-8")
    attach_centifi_logo_inline_if_needed(msg)
    msg.send(fail_silently=False)

    return {
        "ok": True,
        "sent_to": user.email.strip(),
        "expense_count": count,
        "language_used": lang,
    }
