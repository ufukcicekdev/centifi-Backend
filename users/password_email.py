"""Send branded password-reset email (6-digit code in app), language from user profile."""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from core.email_branding import attach_centifi_logo_inline_if_needed, wrap_branded_email_html

from .models import User
from .password_email_copy import otp_email_context

logger = logging.getLogger(__name__)


def send_password_reset_otp_email(*, user: User, plain_code: str) -> bool:
    """
    Returns True if the message was handed to the email backend without raising.
    On failure logs and returns False (caller may still respond generically to the client).
    """
    first = (user.first_name or "").strip()
    ctx = otp_email_context(lang=getattr(user, "language", None) or "", first_name=first, plain_code=plain_code)
    inner = render_to_string(
        "auth/password_reset_otp_inner.html",
        {
            "greeting": ctx["greeting"],
            "body": ctx["body"],
            "code": ctx["code"],
            "footer": ctx["footer"],
        },
    )
    custom_subj = (getattr(settings, "PASSWORD_RESET_EMAIL_SUBJECT", None) or "").strip()
    subject = custom_subj or ctx["subject"]
    html = wrap_branded_email_html(
        inner_html=inner,
        document_title=subject,
        header_subtitle=ctx["header_subtitle"],
        preheader=ctx["preheader"],
        html_lang=ctx["html_lang"],
    )
    plain = ctx["plain_body"]
    from_addr = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "webmaster@localhost"
    to = (user.email or "").strip()
    if not to:
        logger.warning("password reset otp: user %s has no email", user.pk)
        return False
    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain,
        from_email=from_addr,
        to=[to],
    )
    msg.attach_alternative(html, "text/html")
    attach_centifi_logo_inline_if_needed(msg)
    try:
        msg.send(fail_silently=False)
    except Exception:
        logger.exception("password reset otp email failed for user_id=%s", user.pk)
        return False
    return True
