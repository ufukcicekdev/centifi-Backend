"""6-digit password reset codes (HMAC-hashed, short TTL)."""

from __future__ import annotations

import hashlib
import hmac
import secrets

from django.conf import settings


def generate_reset_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_reset_code(user_id: int, code: str) -> str:
    msg = f"{user_id}:{code.strip()}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()
