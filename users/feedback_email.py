"""Notify team when public feedback is submitted."""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from core.email_branding import attach_centifi_logo_inline_if_needed, wrap_branded_email_html

from .models import SiteFeedback

logger = logging.getLogger(__name__)


def _feedback_recipients() -> list[str]:
    raw = (getattr(settings, "FEEDBACK_TO_EMAIL", None) or "info@centifi.app").strip()
    return [e.strip() for e in raw.split(",") if e.strip()]


def send_feedback_notification_email(*, feedback: SiteFeedback) -> bool:
    recipients = _feedback_recipients()
    if not recipients:
        logger.warning("feedback email: no FEEDBACK_TO_EMAIL configured")
        return False

    subject = f"[Centifi Feedback] {feedback.get_category_display()} — {feedback.email}"
    inner = render_to_string(
        "feedback/notification_inner.html",
        {
            "name": (feedback.name or "").strip() or "—",
            "email": feedback.email,
            "category": feedback.get_category_display(),
            "language": feedback.language or "en",
            "source": feedback.source,
            "message": feedback.message,
            "created_at": feedback.created_at,
            "pk": feedback.pk,
        },
    )
    html_body = wrap_branded_email_html(
        inner_html=inner,
        document_title="New feedback",
        header_subtitle="Centifi website",
        preheader=f"From {feedback.email}",
        html_lang="en",
    )
    plain = (
        f"New feedback (#{feedback.pk})\n\n"
        f"From: {(feedback.name or '').strip() or '(no name)'} <{feedback.email}>\n"
        f"Category: {feedback.get_category_display()}\n"
        f"Language: {feedback.language}\n"
        f"Source: {feedback.source}\n\n"
        f"{feedback.message}\n"
    )
    from_addr = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "webmaster@localhost"
    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain,
        from_email=from_addr,
        to=recipients,
        reply_to=[feedback.email],
    )
    msg.attach_alternative(html_body, "text/html")
    attach_centifi_logo_inline_if_needed(msg)
    try:
        msg.send(fail_silently=False)
    except Exception:
        logger.exception("feedback email failed for pk=%s", feedback.pk)
        return False
    return True
