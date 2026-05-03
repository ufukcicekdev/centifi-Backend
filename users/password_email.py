"""Send branded password-reset email (HTML template + optional inline logo)."""

from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from core.email_branding import attach_centifi_logo_inline_if_needed, wrap_branded_email_html

from .models import User

logger = logging.getLogger(__name__)
_token_generator = PasswordResetTokenGenerator()


def build_password_reset_link(user: User) -> str:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = _token_generator.make_token(user)
    base = (getattr(settings, "PASSWORD_RESET_PUBLIC_URL", None) or "").strip().rstrip("/")
    if not base:
        base = "centifi://reset-password"
    joiner = "&" if "?" in base else "?"
    return f"{base}{joiner}uid={uid}&token={token}"


def send_password_reset_email(*, user: User) -> bool:
    """
    Returns True if the message was handed to the email backend without raising.
    On failure logs and returns False (caller may still respond generically to the client).
    """
    first = (user.first_name or "").strip()
    link = build_password_reset_link(user)
    inner = render_to_string(
        "auth/password_reset_inner.html",
        {
            "first_name": first,
            "reset_link": link,
        },
    )
    subject = (getattr(settings, "PASSWORD_RESET_EMAIL_SUBJECT", None) or "").strip() or "Centifi — Reset your password"
    preheader = "Reset your Centifi password — link expires soon."
    html = wrap_branded_email_html(
        inner_html=inner,
        document_title=subject,
        header_subtitle="Password reset",
        preheader=preheader,
    )
    plain = (
        f"Hello{', ' + first if first else ''},\n\n"
        "We received a request to reset your Centifi password.\n"
        "Open this link to set a new password:\n\n"
        f"{link}\n\n"
        "If you did not request this, you can ignore this email.\n"
    )
    from_addr = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "webmaster@localhost"
    to = (user.email or "").strip()
    if not to:
        logger.warning("password reset: user %s has no email", user.pk)
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
        logger.exception("password reset email failed for user_id=%s", user.pk)
        return False
    return True
