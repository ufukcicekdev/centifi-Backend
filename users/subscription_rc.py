"""RevenueCat subscriber payload → User.pro_entitlement_expires_at (entitlement id: ``pro``)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from django.conf import settings

ENTITLEMENT_PRO = getattr(settings, "REVENUECAT_ENTITLEMENT_ID", "pro").strip() or "pro"


def _parse_expires_date(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    s = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def extract_pro_expiry_from_subscriber(subscriber: dict[str, Any]) -> datetime | None:
    """
    Accepts full GET /v1/subscribers/{id} JSON or nested ``subscriber`` from webhooks.
    Returns UTC expiry for entitlement ``pro``, or None if not active.
    """
    sub = subscriber.get("subscriber") or subscriber
    entitlements = sub.get("entitlements") or {}
    pro = entitlements.get(ENTITLEMENT_PRO)
    if not isinstance(pro, dict):
        return None
    expires = _parse_expires_date(pro.get("expires_date"))
    if expires is None:
        return None
    # RevenueCat uses distant future for lifetime; treat as active
    return expires


def update_user_pro_expiry(user, subscriber: dict[str, Any]) -> bool:
    """Mutates and saves user if expiry changed. Returns True if save() called."""
    from .models import User

    assert isinstance(user, User)
    new_exp = extract_pro_expiry_from_subscriber(subscriber)
    old = user.pro_entitlement_expires_at
    if old == new_exp:
        return False
    user.pro_entitlement_expires_at = new_exp
    user.save(update_fields=["pro_entitlement_expires_at"])
    return True


def fetch_revenuecat_subscriber_json(app_user_id: str) -> dict[str, Any] | None:
    """GET https://api.revenuecat.com/v1/subscribers/{app_user_id} — requires secret API key."""
    import json
    import urllib.error
    import urllib.parse
    import urllib.request

    key = (getattr(settings, "REVENUECAT_SECRET_API_KEY", None) or "").strip()
    if not key:
        return None
    safe_id = urllib.parse.quote(str(app_user_id), safe="")
    url = f"https://api.revenuecat.com/v1/subscribers/{safe_id}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None
