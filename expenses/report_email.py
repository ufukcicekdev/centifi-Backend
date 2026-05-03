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


def _render_report_inner_html(rows: list[dict], start: date, end: date, list_label: str) -> str:
    """Intro + table from ``email_templates/reports/expense_report.html``."""
    period = f"{start.isoformat()} – {end.isoformat()}"
    return render_to_string(
        "reports/expense_report.html",
        {
            "rows": rows,
            "period": period,
            "list_label": list_label,
        },
    )


def send_expense_report_email(
    *,
    user: User,
    start: date,
    end: date,
    list_id: int | None = None,
) -> dict:
    """
    Sends multipart email: HTML body (table) + plain-text fallback + CSV attachment.
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

    rows = _rows(user, start, end, list_id)
    count = len(rows)
    csv_text = _build_csv(rows)

    subject = f"Centifi expense report ({start.isoformat()} – {end.isoformat()})"
    if list_label:
        subject += f" — {list_label}"

    inner_html = _render_report_inner_html(rows, start, end, list_label)
    sub_parts = [f"{start.isoformat()} – {end.isoformat()}"]
    if list_label:
        sub_parts.append(list_label)
    header_subtitle = "Expense report · " + " · ".join(sub_parts)
    preheader = f"Centifi expense report: {count} row(s) in this period. CSV attached."
    html_body = wrap_branded_email_html(
        inner_html=inner_html,
        document_title=subject,
        header_subtitle=header_subtitle,
        preheader=preheader,
    )

    text_body = (
        f"Hello,\n\n"
        f"Your Centifi expense report for {start.isoformat()} to {end.isoformat()}"
        f"{' (' + list_label + ')' if list_label else ''} is in the HTML part of this message "
        f"as a table ({count} row(s)). A CSV file is attached for download.\n\n"
        f"— Centifi\n"
    )

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

    return {"ok": True, "sent_to": user.email.strip(), "expense_count": count}
