"""
SMTP2GO HTTP API (v3) email backend — `SMTP2GO_API_KEY` + `SMTP2GO_FROM_EMAIL`.
https://developers.smtp2go.com/reference/send-standard-email
"""

from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.request
from email.mime.base import MIMEBase

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage

logger = logging.getLogger(__name__)


def _smtp2go_mime_is_inline_image(part: MIMEBase) -> bool:
    disp = None
    try:
        disp = part.get_content_disposition()
    except Exception:
        pass
    if disp == "inline" and part.get("Content-ID"):
        return True
    raw = str(part.get("Content-Disposition") or "")
    return "inline" in raw.lower() and bool(part.get("Content-ID"))


def _smtp2go_mime_to_blob_dict(part: MIMEBase) -> dict:
    fn = part.get_filename() or "attachment"
    raw = part.get_payload(decode=True)
    if raw is None:
        pl = part.get_payload()
        raw = pl.encode("utf-8", errors="replace") if isinstance(pl, str) else b""
    ctype = part.get_content_type() or "application/octet-stream"
    return {
        "filename": str(fn),
        "fileblob": base64.b64encode(bytes(raw)).decode("ascii"),
        "mimetype": str(ctype),
    }


def _smtp2go_send_url() -> str:
    return (getattr(settings, "SMTP2GO_API_URL", None) or "https://api.smtp2go.com/v3/email/send").strip()


def _smtp2go_payload_from_email(msg: EmailMessage) -> dict:
    text_body = (msg.body or "").strip()
    html_body = ""
    for content, mimetype in getattr(msg, "alternatives", []) or []:
        if mimetype == "text/html":
            html_body = content if isinstance(content, str) else str(content, "utf-8", errors="replace")
            break

    attachments: list[dict] = []
    inlines: list[dict] = []
    for attachment in msg.attachments:
        if isinstance(attachment, MIMEBase):
            if _smtp2go_mime_is_inline_image(attachment):
                inlines.append(_smtp2go_mime_to_blob_dict(attachment))
            else:
                attachments.append(_smtp2go_mime_to_blob_dict(attachment))
            continue
        if len(attachment) == 3:
            filename, content, mimetype = attachment
        else:
            filename, content = attachment[0], attachment[1]
            mimetype = "application/octet-stream"
        if isinstance(content, str):
            raw = content.encode("utf-8")
        else:
            raw = bytes(content)
        attachments.append(
            {
                "filename": str(filename),
                "fileblob": base64.b64encode(raw).decode("ascii"),
                "mimetype": str(mimetype or "application/octet-stream"),
            },
        )

    sender = (msg.from_email or "").strip() or getattr(settings, "SMTP2GO_FROM_EMAIL", "").strip()
    payload: dict = {
        "api_key": settings.SMTP2GO_API_KEY,
        "sender": sender,
        "to": list(msg.to or []),
        "subject": msg.subject or "",
        "text_body": text_body or "(no plain text body)",
    }
    if html_body:
        payload["html_body"] = html_body
    if msg.cc:
        payload["cc"] = list(msg.cc)
    if msg.bcc:
        payload["bcc"] = list(msg.bcc)
    if attachments:
        payload["attachments"] = attachments
    if inlines:
        payload["inlines"] = inlines
    return payload


def _smtp2go_send_json(payload: dict) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        _smtp2go_send_url(),
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "X-Smtp2go-Api-Key": str(payload.get("api_key") or ""),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        logger.error("SMTP2GO HTTP %s: %s", e.code, err_body[:2000])
        raise RuntimeError(f"SMTP2GO HTTP {e.code}: {err_body[:500]}") from e
    except urllib.error.URLError as e:
        logger.exception("SMTP2GO network error")
        raise RuntimeError(f"SMTP2GO request failed: {e}") from e

    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError as e:
        logger.error("SMTP2GO non-JSON response: %s", raw[:2000])
        raise RuntimeError("SMTP2GO returned invalid JSON") from e


def _smtp2go_response_ok(data: dict) -> tuple[bool, str]:
    """SMTP2GO returns HTTP 200 + JSON; failures usually include an `errors` array."""
    if not isinstance(data, dict):
        return False, "empty response"
    top_err = data.get("errors")
    if top_err:
        return False, json.dumps(top_err, ensure_ascii=False)[:2000]
    d = data.get("data")
    if isinstance(d, dict):
        if d.get("errors"):
            return False, json.dumps(d["errors"], ensure_ascii=False)[:2000]
        if d.get("error"):
            return False, str(d["error"])
    if (data.get("result") or "").lower() in ("error", "failed"):
        return False, json.dumps(data, ensure_ascii=False)[:2000]
    return True, ""


class Smtp2goApiEmailBackend(BaseEmailBackend):
    """Send mail via SMTP2GO JSON API (no SMTP socket)."""

    def send_messages(self, email_messages: list[EmailMessage]) -> int:
        if not email_messages:
            return 0
        if not getattr(settings, "SMTP2GO_API_KEY", "").strip():
            raise RuntimeError("SMTP2GO_API_KEY is not set.")
        if not getattr(settings, "SMTP2GO_FROM_EMAIL", "").strip():
            raise RuntimeError("SMTP2GO_FROM_EMAIL is not set.")

        num_sent = 0
        for msg in email_messages:
            self._send(msg)
            num_sent += 1
        return num_sent

    def _send(self, msg: EmailMessage) -> None:
        payload = _smtp2go_payload_from_email(msg)
        data = _smtp2go_send_json(payload)
        ok, err = _smtp2go_response_ok(data)
        if not ok:
            logger.error("SMTP2GO send rejected: %s", err or data)
            raise RuntimeError(f"SMTP2GO rejected message: {err or 'unknown error'}")
