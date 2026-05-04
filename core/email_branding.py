"""
Centifi transactional email shell: logo, wordmark, footer, preheader.
HTML layout lives under ``backend/email_templates/`` (see ``layout_base.html``).

Logo: ``core/email_assets/centifi-logo-email.png`` is attached inline; HTML uses ``cid:centifi-logo.png``
so clients like Gmail show it. If the file is missing, a purple “C” monogram is used instead.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.mail.message import EmailMessage
from django.template.loader import render_to_string
from email.mime.image import MIMEImage

_ASSETS_DIR = Path(__file__).resolve().parent / "email_assets"
_LOGO_PNG = _ASSETS_DIR / "centifi-logo-email.png"

# SMTP2GO / MIME: ``<img src="cid:…">`` must match this filename in ``inlines`` / Content-ID.
EMAIL_LOGO_INLINE_CID_FILENAME = "centifi-logo.png"


def _logo_block_context(logo_size: int = 48) -> dict:
    try:
        if _LOGO_PNG.is_file() and _LOGO_PNG.stat().st_size > 0:
            return {
                "logo_mode": "cid",
                "logo_cid_filename": EMAIL_LOGO_INLINE_CID_FILENAME,
                "logo_size": logo_size,
            }
    except OSError:
        pass
    return {
        "logo_mode": "monogram",
        "logo_cid_filename": "",
        "logo_size": logo_size,
    }


def attach_centifi_logo_inline_if_needed(msg: EmailMessage) -> None:
    """When the layout uses ``cid:…`` for the logo, attach the PNG as an inline MIME part."""
    if _logo_block_context()["logo_mode"] != "cid":
        return
    try:
        raw = _LOGO_PNG.read_bytes()
    except OSError:
        return
    img = MIMEImage(raw, _subtype="png")
    img.add_header("Content-ID", f"<{EMAIL_LOGO_INLINE_CID_FILENAME}>")
    img.add_header("Content-Disposition", "inline", filename=EMAIL_LOGO_INLINE_CID_FILENAME)
    msg.attach(img)


def wrap_branded_email_html(
    *,
    inner_html: str,
    document_title: str,
    header_subtitle: str = "",
    preheader: str = "",
    app_url: str | None = None,
    html_lang: str = "en",
) -> str:
    """Wraps inner HTML in the table-based layout from ``email_templates/layout_base.html``."""
    title = document_title or "Centifi"
    pre = (preheader or "")[:220]
    site = (app_url or getattr(settings, "EMAIL_APP_URL", None) or "https://centifi.app").strip().rstrip("/")
    lang = (html_lang or "en").strip().lower().split("-")[0] or "en"

    ctx = {
        "html_lang": lang,
        "document_title": title,
        "header_subtitle": header_subtitle or "",
        "preheader": pre,
        "site_href": site,
        "site_label": site,
        "inner_html": inner_html,
        **_logo_block_context(48),
    }
    return render_to_string("layout_base.html", ctx)
