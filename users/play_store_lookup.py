"""Fetch app name + icon from a public Google Play HTML page (best-effort)."""

from __future__ import annotations

import html as html_module
import re
import urllib.error
import urllib.parse
import urllib.request


PLAY_STORE_UA = (
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
)


def package_name_from_store_url(store_url: str) -> str:
    u = (store_url or "").strip()
    if not u:
        return ""
    m = re.search(r"[?&]id=([^&]+)", u, re.I)
    if m:
        return urllib.parse.unquote(m.group(1).strip())
    return ""


def fetch_play_store_meta(package_name: str) -> tuple[str | None, str | None]:
    """
    Returns (app_title, icon_https_url).
    Either may be None if parsing fails.
    """
    pkg = (package_name or "").strip()
    if not pkg or not re.match(r"^[a-zA-Z][a-zA-Z0-9._]*$", pkg):
        return None, None

    url = "https://play.google.com/store/apps/details?id=" + urllib.parse.quote(pkg)
    req = urllib.request.Request(url, headers={"User-Agent": PLAY_STORE_UA, "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        return None, None

    icon = _og_content(raw, "og:image")
    title = _og_content(raw, "og:title")
    if title:
        title = html_module.unescape(title)
        for suffix in (" - Apps on Google Play", " – Apps on Google Play", " \u2013 Apps on Google Play"):
            if title.endswith(suffix):
                title = title[: -len(suffix)].strip()
                break
    if icon:
        icon = html_module.unescape(icon)
    return title or None, icon or None


def _og_content(page: str, prop: str) -> str | None:
    esc = re.escape(prop)
    for pat in (
        rf'<meta\s+property="{esc}"\s+content="([^"]*)"',
        rf'<meta\s+content="([^"]*)"\s+property="{esc}"',
    ):
        m = re.search(pat, page, re.I | re.DOTALL)
        if m:
            return m.group(1).strip() or None
    return None
