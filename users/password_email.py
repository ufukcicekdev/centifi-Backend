"""Send branded password-reset email (6-digit code in app)."""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from core.email_branding import attach_centifi_logo_inline_if_needed, wrap_branded_email_html

from .models import User

logger = logging.getLogger(__name__)


def send_password_reset_otp_email(*, user: User, plain_code: str) -> bool:
    """
    Returns True if the message was handed to the email backend without raising.
    On failure logs and returns False (caller may still respond generically to the client).
    """
    first = (user.first_name or "").strip()
    inner = render_to_string(
        "auth/password_reset_otp_inner.html",
        {
            "first_name": first,
            "code": plain_code,
        },
    )
    subject = (getattr(settings, "PASSWORD_RESET_EMAIL_SUBJECT", None) or "").strip() or "Centifi — Your password reset code"
    preheader = "Your Centifi password reset code — expires in 15 minutes."
    html = wrap_branded_email_html(
        inner_html=inner,
        document_title=subject,
        header_subtitle="Password reset",
        preheader=preheader,
    )
    plain = (
        f"Hello{', ' + first if first else ''},\n\n"
        "We received a request to reset your Centifi password.\n"
        "Enter this 6-digit code in the app (valid 15 minutes):\n\n"
        f"{plain_code}\n\n"
        "If you did not request this, you can ignore this email.\n"
    )
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
