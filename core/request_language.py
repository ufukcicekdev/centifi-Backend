"""Resolve email/UI language from an API request (body, headers, user profile)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from users.password_email_copy import normalize_email_language

if TYPE_CHECKING:
    from django.http import HttpRequest

    from users.models import User


def _first_accept_language_tag(raw: str) -> str:
    for part in raw.split(","):
        tag = part.split(";")[0].strip()
        if tag:
            return tag
    return ""


def resolve_email_language(
    *,
    request: HttpRequest | None,
    body_language: str | None = None,
    user: User | None = None,
) -> str:
    """
    Priority: JSON body ``language`` → ``X-Centifi-Language`` → ``user.language``
    → ``Accept-Language`` → ``en``.
    """
    candidates: list[str] = []

    body = (body_language or "").strip()
    if body:
        candidates.append(body)

    if request is not None:
        header = (request.META.get("HTTP_X_CENTIFI_LANGUAGE") or "").strip()
        if header:
            candidates.append(header)
        accept = (request.META.get("HTTP_ACCEPT_LANGUAGE") or "").strip()
        if accept:
            tag = _first_accept_language_tag(accept)
            if tag:
                candidates.append(tag)

    if user is not None:
        profile_lang = (getattr(user, "language", None) or "").strip()
        if profile_lang:
            candidates.append(profile_lang)

    for candidate in candidates:
        return normalize_email_language(candidate)
    return "en"
