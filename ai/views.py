import logging
import os
import io
import json
import re
import base64
import uuid
from datetime import date

import boto3
from botocore.client import Config
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import ParseTextSerializer, ParseImageSerializer

logger = logging.getLogger(__name__)

EXPENSE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "amount": {"type": "number"},
        "description": {"type": "string"},
        "category": {
            "type": "string",
            "enum": ["food", "transport", "shopping", "health", "entertainment", "utilities", "other"],
        },
        "date": {"type": "string"},
        "currency": {"type": "string"},
    },
    "required": ["amount", "description", "category", "date", "currency"],
}

EXPENSE_BATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "expenses": {
            "type": "array",
            "items": EXPENSE_ITEM_SCHEMA,
            "minItems": 1,
        },
    },
    "required": ["expenses"],
}

ALLOWED_CATEGORIES = frozenset(
    {"food", "transport", "shopping", "health", "entertainment", "utilities", "other"}
)


def _get_gemini_client():
    # Railway/console bazen başta/sonda boşluk veya yanlış tırnak bırakabiliyor
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip().strip('"').strip("'")
    if not api_key:
        logger.warning("GEMINI_API_KEY missing or empty in process env")
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception:
        logger.exception("google-genai client failed to initialize (wrong package version or bad key format?)")
        return None


def _gemini_model_id() -> str:
    # gemini-2.0-flash yeni anahtarlarda API'de 404 (Google: "no longer available to new users")
    return (os.getenv("GEMINI_MODEL") or "gemini-2.5-flash").strip()


def _extract_generate_content_text(resp) -> str:
    """google-genai sürümleri / güvenlik filtreleri bazen `resp.text` boş bırakır; candidates üzerinden dene."""
    if resp is None:
        return ""
    t = getattr(resp, "text", None)
    if isinstance(t, str) and t.strip():
        return t
    try:
        for c in getattr(resp, "candidates", None) or []:
            content = getattr(c, "content", None)
            if content is None:
                continue
            for part in getattr(content, "parts", None) or []:
                pt = getattr(part, "text", None)
                if isinstance(pt, str) and pt.strip():
                    return pt
    except Exception:
        logger.exception("_extract_generate_content_text: unexpected response shape")
    return ""


def _parse_gemini_json_any(text: str):
    """Gemini çıktısı: tek nesne, `expenses` nesnesi veya kök düz dizi."""
    raw = (text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except Exception:
        return None


def _coerce_root_to_expenses_payload(parsed) -> dict | None:
    if parsed is None:
        return None
    if isinstance(parsed, list):
        items = [x for x in parsed if isinstance(x, dict)]
        return {"expenses": items} if items else None
    if isinstance(parsed, dict):
        if "expenses" in parsed and isinstance(parsed["expenses"], list):
            items = [x for x in parsed["expenses"] if isinstance(x, dict)]
            return {"expenses": items} if items else None
        if all(k in parsed for k in ("amount", "description", "category", "date", "currency")):
            return {"expenses": [parsed]}
    return None


def _sanitize_expense_item(item: dict) -> dict:
    cat = str(item.get("category") or "other").lower()
    if cat not in ALLOWED_CATEGORIES:
        cat = "other"
    try:
        amount = float(item.get("amount"))
    except (TypeError, ValueError):
        amount = 0.0
    desc = str(item.get("description") or "").strip()[:500] or "Expense"
    dt = str(item.get("date") or "")[:32]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", dt):
        dt = date.today().isoformat()
    cur = str(item.get("currency") or "USD").strip().upper()[:8] or "USD"
    return {"amount": amount, "description": desc, "category": cat, "date": dt, "currency": cur}


def _finalize_expenses_batch(coerced: dict, fallback_text: str, receipt_url: str | None = None) -> dict:
    raw_list = list(coerced.get("expenses") or [])
    sanitized = [_sanitize_expense_item(x) for x in raw_list if isinstance(x, dict)]
    if not sanitized:
        sanitized = [_sanitize_expense_item(_fallback_parse(fallback_text))]
    out: dict = {"expenses": sanitized}
    if receipt_url:
        out["receipt_url"] = receipt_url
    return out


def _build_batch_response(parsed_any, fallback_text: str, receipt_url: str | None = None) -> dict:
    coerced = _coerce_root_to_expenses_payload(parsed_any)
    if not coerced:
        coerced = {"expenses": [_fallback_parse(fallback_text)]}
    return _finalize_expenses_batch(coerced, fallback_text=fallback_text, receipt_url=receipt_url)


def _fallback_parse(text: str) -> dict:
    lower = text.lower()
    category = "other"
    if any(k in lower for k in ["coffee", "cafe", "restaurant", "food", "lunch", "dinner", "yemek", "kahve"]):
        category = "food"
    elif any(k in lower for k in ["uber", "bus", "metro", "taxi", "transport", "ulaşım"]):
        category = "transport"
    elif any(k in lower for k in ["rent", "electric", "water", "internet", "bill", "fatura"]):
        category = "utilities"
    elif any(k in lower for k in ["pharmacy", "doctor", "hospital", "sağlık"]):
        category = "health"
    elif any(k in lower for k in ["movie", "cinema", "game", "eğlence"]):
        category = "entertainment"
    elif any(k in lower for k in ["shopping", "amazon", "market", "alışveriş"]):
        category = "shopping"
    amount_match = re.search(r"(?<!\d)(\d+(?:[.,]\d{1,2})?)", text)
    amount = float(amount_match.group(1).replace(",", ".")) if amount_match else 0.0
    return {
        "amount": amount if amount > 0 else 5.5,
        "description": text.strip()[:255] or "Expense",
        "category": category,
        "date": date.today().isoformat(),
        "currency": "USD",
    }


def _upload_to_spaces(data: bytes, mime_type: str, folder: str = "receipts") -> str | None:
    """Upload raw bytes to DigitalOcean Spaces and return the public URL."""
    key_id = os.getenv("AWS_ACCESS_KEY_ID")
    secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    bucket = os.getenv("AWS_STORAGE_BUCKET_NAME")
    region = os.getenv("AWS_S3_REGION_NAME")
    endpoint = os.getenv("AWS_S3_ENDPOINT_URL")
    if not all([key_id, secret, bucket, endpoint]):
        return None
    try:
        ext = mime_type.split("/")[-1].replace("jpeg", "jpg")
        key = f"{folder}/{uuid.uuid4()}.{ext}"
        client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint,
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
            config=Config(signature_version="s3v4"),
        )
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=mime_type,
            ACL="public-read",
        )
        return f"{endpoint}/{bucket}/{key}"
    except Exception:
        return None


def _gemini_parse_text_raw(text: str, language: str = "en"):
    client = _get_gemini_client()
    if not client:
        return None
    lang_name = LANGUAGE_NAMES.get(language, "English")
    prompt = (
        f"The user wrote in {lang_name}: \"{text}\"\n"
        "Extract expense records. Detect currency from context (₺/TL→TRY, $→USD, €→EUR, £→GBP). "
        "If the user mentions MULTIPLE distinct expenses in one message "
        "(e.g. food 10 TL and cinema 20 TL), put each in the \"expenses\" array as a separate object. "
        "If there is only one expense, still use \"expenses\" with exactly one element.\n"
        "Return ONLY valid JSON matching this schema.\n"
        f"Schema: {json.dumps(EXPENSE_BATCH_SCHEMA)}"
    )
    try:
        resp = client.models.generate_content(
            model=_gemini_model_id(),
            contents=prompt,
        )
        raw = _extract_generate_content_text(resp)
        if not raw.strip():
            logger.warning("Gemini returned empty text for parse-text request")
            return None
        return _parse_gemini_json_any(raw)
    except Exception:
        logger.exception("gemini_parse_text failed model=%s", _gemini_model_id())
        return None


def _gemini_parse_media(data_b64: str, mime_type: str, prompt_text: str, client=None):
    if client is None:
        client = _get_gemini_client()
    if not client:
        return None
    try:
        from google.genai import types
        prompt = (
            f"{prompt_text} "
            "Return ONLY valid JSON matching this schema. "
            "If there are MULTIPLE distinct expenses or line items, include each as a separate element in \"expenses\". "
            "If only one total applies, use \"expenses\" with one element.\n"
            "For date use YYYY-MM-DD format. "
            "For currency detect from content or default to USD.\n"
            f"Schema: {json.dumps(EXPENSE_BATCH_SCHEMA)}"
        )
        part = types.Part.from_bytes(data=base64.b64decode(data_b64), mime_type=mime_type)
        resp = client.models.generate_content(
            model=_gemini_model_id(),
            contents=[prompt, part],
        )
        raw = _extract_generate_content_text(resp)
        if not raw.strip():
            logger.warning("Gemini returned empty text for media mime_type=%s", mime_type)
            return None
        return _parse_gemini_json_any(raw)
    except Exception:
        logger.exception("gemini_parse_media failed model=%s mime=%s", _gemini_model_id(), mime_type)
        return None


class ParseTextView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = ParseTextSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        text = ser.validated_data["input"]
        language = ser.validated_data.get("language", "en")
        parsed_any = _gemini_parse_text_raw(text, language)
        data = _build_batch_response(parsed_any, fallback_text=text)
        return Response(data)


class ParseImageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = ParseImageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        image_b64 = ser.validated_data["image"]
        mime_type = ser.validated_data.get("mime_type", "image/jpeg")

        # Upload to Spaces in background (non-blocking best-effort)
        receipt_url = None
        try:
            image_bytes = base64.b64decode(image_b64)
            receipt_url = _upload_to_spaces(image_bytes, mime_type, folder="receipts")
        except Exception:
            pass

        parsed_any = _gemini_parse_media(
            image_b64,
            mime_type,
            "This is a receipt or expense document. Extract every distinct expense or line item.",
        )
        data = _build_batch_response(parsed_any, fallback_text="", receipt_url=receipt_url)
        return Response(data)


LANGUAGE_NAMES = {
    "en": "English", "tr": "Turkish", "de": "German",
    "fr": "French", "es": "Spanish",
}


class ParseAudioView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = ParseImageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        audio_b64 = ser.validated_data["image"]
        mime_type = ser.validated_data.get("mime_type", "audio/m4a")
        language = ser.validated_data.get("language", "en")
        lang_name = LANGUAGE_NAMES.get(language, "English")

        # Upload audio clip to Spaces for audit trail
        try:
            audio_bytes = base64.b64decode(audio_b64)
            _upload_to_spaces(audio_bytes, mime_type, folder="audio")
        except Exception:
            pass

        prompt = (
            f"The user is speaking in {lang_name}. "
            "They are describing personal expense(s) verbally (e.g. '15 tl yemek' means 15 TRY food expense). "
            "If they mention MULTIPLE expenses in one recording (e.g. food 10 TL and cinema 20 TL), "
            "put each in the \"expenses\" array as a separate object. "
            "Transcribe their speech and extract fields for each expense. "
            "Detect the currency from context (₺/TL → TRY, $ → USD, € → EUR, £ → GBP). "
            "If no currency mentioned, use the user's likely local currency based on language. "
        )
        gemini_client = _get_gemini_client()
        if not gemini_client:
            return Response(
                {
                    "detail": "Gemini kullanılamıyor (/sunucuda GEMINI_API_KEY boş veya google-genai paketi hatalı).",
                    "code": "GEMINI_CLIENT_UNAVAILABLE",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        parsed_any = _gemini_parse_media(audio_b64, mime_type, prompt, client=gemini_client)
        if parsed_any is None:
            return Response(
                {
                    "detail": (
                        "Ses Gemini tarafından JSON’a çevrilemedi veya boş yanıt geldi. "
                        "Railway’de GEMINI_MODEL deneyin: gemini-2.5-flash veya gemini-2.5-flash-lite-latest; "
                        "deploy loglarına bakın (ai.views)."
                    ),
                    "code": "GEMINI_AUDIO_PARSE_FAILED",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        data = _build_batch_response(parsed_any, fallback_text="", receipt_url=None)
        return Response(data)
