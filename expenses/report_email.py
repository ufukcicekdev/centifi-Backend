"""Expense report email: HTML table in body + CSV attachment (SMTP2GO / any SMTP)."""

import csv
import io
from datetime import date
from html import escape

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives

from .models import Expense, ExpenseList

User = get_user_model()


def _smtp_ready() -> bool:
    backend = (getattr(settings, "EMAIL_BACKEND", "") or "").lower()
    if "console" in backend or "locmem" in backend or "dummy" in backend:
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


def _build_html_table(rows: list[dict], start: date, end: date, list_label: str) -> str:
    """Simple HTML table for mail clients; all cells escaped."""
    period = f"{escape(start.isoformat())} – {escape(end.isoformat())}"
    header_extra = f" · {escape(list_label)}" if list_label else ""

    if not rows:
        body = "<p>No expenses in this period.</p>"
    else:
        cells = []
        for r in rows:
            kind = "Income" if r["is_income"] else "Expense"
            cells.append(
                "<tr>"
                f"<td style='padding:8px;border:1px solid #ddd;'>{escape(r['date'])}</td>"
                f"<td style='padding:8px;border:1px solid #ddd;text-align:right;'>"
                f"{escape(r['currency'])} {r['amount']:.2f}</td>"
                f"<td style='padding:8px;border:1px solid #ddd;'>{escape(r['category'])}</td>"
                f"<td style='padding:8px;border:1px solid #ddd;'>{escape(r['description'])}</td>"
                f"<td style='padding:8px;border:1px solid #ddd;'>{escape(r['list'] or '—')}</td>"
                f"<td style='padding:8px;border:1px solid #ddd;'>{escape(kind)}</td>"
                "</tr>",
            )
        body = (
            "<table style='border-collapse:collapse;width:100%;max-width:720px;"
            "font-family:system-ui,-apple-system,sans-serif;font-size:14px;'>"
            "<thead><tr>"
            "<th style='padding:8px;border:1px solid #ccc;background:#f0f0f0;text-align:left;'>Date</th>"
            "<th style='padding:8px;border:1px solid #ccc;background:#f0f0f0;text-align:right;'>Amount</th>"
            "<th style='padding:8px;border:1px solid #ccc;background:#f0f0f0;text-align:left;'>Category</th>"
            "<th style='padding:8px;border:1px solid #ccc;background:#f0f0f0;text-align:left;'>Description</th>"
            "<th style='padding:8px;border:1px solid #ccc;background:#f0f0f0;text-align:left;'>List</th>"
            "<th style='padding:8px;border:1px solid #ccc;background:#f0f0f0;text-align:left;'>Type</th>"
            "</tr></thead><tbody>"
            + "".join(cells)
            + "</tbody></table>"
        )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:16px;background:#fafafa;color:#111;">
  <p style="font-family:system-ui,-apple-system,sans-serif;font-size:15px;">
    Hello,<br><br>
    Here is your Centifi expense report for <strong>{period}</strong>{header_extra}.
    A <strong>CSV</strong> file is attached if you want to import or archive the data.
  </p>
  {body}
  <p style="font-family:system-ui,-apple-system,sans-serif;font-size:13px;color:#666;margin-top:20px;">
    — Centifi
  </p>
</body></html>"""


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
            "Set EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL "
            "(e.g. SMTP2GO: mail.smtp2go.com, port 2525 or 587).",
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
    html_body = _build_html_table(rows, start, end, list_label)

    subject = f"Centifi expense report ({start.isoformat()} – {end.isoformat()})"
    if list_label:
        subject += f" — {list_label}"

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
    msg.send(fail_silently=False)

    return {"ok": True, "sent_to": user.email.strip(), "expense_count": count}
