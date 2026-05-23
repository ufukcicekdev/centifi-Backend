"""Notify team when someone applies to be a test user."""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from core.email_branding import attach_centifi_logo_inline_if_needed, wrap_branded_email_html

from .models import TestUserApplication

logger = logging.getLogger(__name__)


def _recipients() -> list[str]:
    raw = (
        getattr(settings, "TEST_USERS_TO_EMAIL", None)
        or getattr(settings, "FEEDBACK_TO_EMAIL", None)
        or "info@centifi.app"
    ).strip()
    return [e.strip() for e in raw.split(",") if e.strip()]


def send_test_user_notification_email(*, application: TestUserApplication) -> bool:
    recipients = _recipients()
    if not recipients:
        return False

    subject = f"[Centifi Test User] {application.get_platform_display()} — {application.email}"
    inner = render_to_string(
        "test_users/notification_inner.html",
        {
            "email": application.email,
            "platform": application.get_platform_display(),
            "language": application.language or "en",
            "source": application.source,
            "created_at": application.created_at,
            "pk": application.pk,
        },
    )
    html_body = wrap_branded_email_html(
        inner_html=inner,
        document_title="New test user signup",
        header_subtitle="Centifi website",
        preheader=f"{application.email} · {application.get_platform_display()}",
        html_lang="en",
    )
    plain = (
        f"New test user application (#{application.pk})\n\n"
        f"Email: {application.email}\n"
        f"Platform: {application.get_platform_display()}\n"
        f"Language: {application.language}\n"
        f"Source: {application.source}\n"
    )
    from_addr = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "webmaster@localhost"
    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain,
        from_email=from_addr,
        to=recipients,
        reply_to=[application.email],
    )
    msg.attach_alternative(html_body, "text/html")
    attach_centifi_logo_inline_if_needed(msg)
    try:
        msg.send(fail_silently=False)
    except Exception:
        logger.exception("test user email failed for pk=%s", application.pk)
        return False
    return True
