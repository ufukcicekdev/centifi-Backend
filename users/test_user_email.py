"""Notify team when someone applies to be a test user."""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from core.email_branding import attach_centifi_logo_inline_if_needed, wrap_branded_email_html

from .models import TestUserApplication
from .test_user_invite_copy import invite_email_context

logger = logging.getLogger(__name__)


def invite_url_for_application(application: TestUserApplication) -> str:
    if application.platform == TestUserApplication.Platform.IOS:
        return (getattr(settings, "TEST_USER_IOS_INVITE_URL", None) or "").strip()
    return (getattr(settings, "TEST_USER_ANDROID_INVITE_URL", None) or "").strip()


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


def send_test_user_invite_email(*, application: TestUserApplication) -> tuple[bool, str]:
    """
    Send invite email to the applicant. Returns (success, error_message).
    error_message is empty on success.
    """
    invite_url = invite_url_for_application(application)
    if not invite_url:
        which = "TEST_USER_IOS_INVITE_URL" if application.platform == TestUserApplication.Platform.IOS else "TEST_USER_ANDROID_INVITE_URL"
        return False, f"Missing {which} in server settings."

    platform_label = application.get_platform_display()
    ctx = invite_email_context(
        lang=application.language,
        platform_label=platform_label,
        invite_url=invite_url,
    )
    inner = render_to_string(
        "test_users/invite_inner.html",
        {
            "greeting": ctx["greeting"],
            "body": ctx["body"],
            "cta": ctx["cta"].format(platform=platform_label),
            "invite_url": invite_url,
            "footer": ctx["footer"],
        },
    )
    html_body = wrap_branded_email_html(
        inner_html=inner,
        document_title=ctx["subject"],
        header_subtitle=ctx["header_subtitle"],
        preheader=ctx["preheader"],
        html_lang=ctx["html_lang"],
    )
    from_addr = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "webmaster@localhost"
    msg = EmailMultiAlternatives(
        subject=ctx["subject"],
        body=ctx["plain_body"],
        from_email=from_addr,
        to=[application.email],
        reply_to=_recipients()[:1] or ["info@centifi.app"],
    )
    msg.attach_alternative(html_body, "text/html")
    attach_centifi_logo_inline_if_needed(msg)
    try:
        msg.send(fail_silently=False)
    except Exception:
        logger.exception("test user invite email failed for pk=%s", application.pk)
        return False, "Email delivery failed (check SMTP2GO / logs)."
    return True, ""
