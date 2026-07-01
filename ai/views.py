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
from celery import shared_task
from django.core.cache import cache
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import ParseTextSerializer, ParseImageSerializer, SpendingInsightsSerializer

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
        "is_income": {"type": "boolean"},
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
    raw_income = item.get("is_income")
    is_income = raw_income is True
    return {
        "amount": amount,
        "description": desc,
        "category": cat,
        "date": dt,
        "currency": cur,
        "is_income": is_income,
    }


def _merge_receipt_lines_by_category(items: list[dict]) -> list[dict]:
    """
    Fişte aynı kategorideki satırları (yemek, ulaşım, …) tek harcamada toplar.
    Metin/ses çoklu niyet (farklı kategoriler) ayrı kalır; sadece aynı (cat,date,currency) gruplanır.
    """
    if len(items) <= 1:
        return items

    # (category, date, currency) -> list of items
    buckets: dict[tuple[str, str, str], list[dict]] = {}
    for it in items:
        key = (it["category"], it["date"], it["currency"], bool(it.get("is_income")))
        buckets.setdefault(key, []).append(it)

    merged: list[dict] = []
    for key, group in buckets.items():
        if len(group) == 1:
            merged.append(group[0])
            continue
        total = round(sum(float(x["amount"]) for x in group), 2)
        # Açıklamalar: kısa benzersiz parçalar
        parts: list[str] = []
        seen: set[str] = set()
        for x in group:
            d = (x.get("description") or "").strip()
            if d and d not in seen:
                seen.add(d)
                parts.append(d[:120])
        if len(parts) <= 4:
            desc = " · ".join(parts)[:500]
        else:
            head = " · ".join(parts[:3])
            desc = f"{head} (+{len(parts) - 3} kalem)"[:500]
        cat, dt, cur, is_income = key
        merged.append(
            {
                "amount": total,
                "description": desc or group[0]["description"],
                "category": cat,
                "date": dt,
                "currency": cur,
                "is_income": is_income,
            }
        )

    # Orijinal fiş sırasına yakın: kategori sabit sırayla
    cat_order = [
        "food",
        "transport",
        "shopping",
        "health",
        "entertainment",
        "utilities",
        "other",
    ]
    rank = {c: i for i, c in enumerate(cat_order)}

    def sort_key(row: dict) -> tuple[int, str]:
        return (rank.get(row["category"], 99), row["date"])

    merged.sort(key=sort_key)
    return merged


def _finalize_expenses_batch(
    coerced: dict,
    fallback_text: str,
    receipt_url: str | None = None,
    *,
    merge_receipt_by_category: bool = False,
    expense_date_today: bool = False,
) -> dict:
    raw_list = list(coerced.get("expenses") or [])
    sanitized = [_sanitize_expense_item(x) for x in raw_list if isinstance(x, dict)]
    if not sanitized:
        sanitized = [_sanitize_expense_item(_fallback_parse(fallback_text))]
    if merge_receipt_by_category:
        sanitized = _merge_receipt_lines_by_category(sanitized)
    if expense_date_today:
        today_iso = date.today().isoformat()
        for x in sanitized:
            x["date"] = today_iso
    out: dict = {"expenses": sanitized}
    if receipt_url:
        out["receipt_url"] = receipt_url
    return out


def _build_batch_response(
    parsed_any,
    fallback_text: str,
    receipt_url: str | None = None,
    *,
    merge_receipt_by_category: bool = False,
    expense_date_today: bool = False,
) -> dict:
    coerced = _coerce_root_to_expenses_payload(parsed_any)
    if not coerced:
        coerced = {"expenses": [_fallback_parse(fallback_text)]}
    return _finalize_expenses_batch(
        coerced,
        fallback_text=fallback_text,
        receipt_url=receipt_url,
        merge_receipt_by_category=merge_receipt_by_category,
        expense_date_today=expense_date_today,
    )


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
        "Set is_income true when the user describes money received (salary, payment, refund, maaş, gelir, kazanç, ödeme aldım). "
        "Otherwise is_income false for spending.\n"
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
            "If only one total applies, use \"expenses\" with one element. "
            "Set is_income true for income/refunds/salary (maaş, gelir, payment received); false for spending.\n"
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




@shared_task(name="ai.tasks.upload_receipt_async")
def upload_receipt_async(image_b64: str, mime_type: str, request_id: str) -> dict:
    """
    Background task to upload receipt image to DigitalOcean Spaces.
    Results cached for 24 hours with request_id key.
    """
    try:
        image_bytes = base64.b64decode(image_b64)
        receipt_url = _upload_to_spaces(image_bytes, mime_type, folder="receipts")
        
        # Cache success with 24h TTL
        result = {"status": "success", "url": receipt_url}
        cache.set(f"receipt_upload:{request_id}", result, 86400)
        
        logger.info(f"Receipt uploaded async: {request_id} → {receipt_url}")
        return result
        
    except Exception as e:
        # Cache failure
        result = {"status": "failed", "reason": str(e)}
        cache.set(f"receipt_upload:{request_id}", result, 86400)
        
        logger.error(f"Receipt upload async failed: {request_id} - {e}")
        return result


class ReceiptUploadStatusView(APIView):
    """
    GET /api/ai/receipt-upload-status/{request_id}/
    
    Check async receipt upload status.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, request_id: str):
        result = cache.get(f"receipt_upload:{request_id}")
        
        if result is None:
            return Response(
                {"status": "pending", "message": "Upload in progress or not found"},
                status=status.HTTP_202_ACCEPTED
            )
        
        if result.get("status") == "failed":
            return Response(result, status=status.HTTP_200_OK)
        
        return Response(result, status=status.HTTP_200_OK)

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
        except Exception as exc:
            logger.error("Receipt upload to Spaces failed: %s", exc)

        parsed_any = _gemini_parse_media(
            image_b64,
            mime_type,
            "This is a receipt or expense document. Extract each printed line with amount and category; "
            "the server will merge lines that share the same category into one total per category.",
        )
        data = _build_batch_response(
            parsed_any,
            fallback_text="",
            receipt_url=receipt_url,
            merge_receipt_by_category=True,
            expense_date_today=True,
        )
        
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
            "They are describing personal expense(s) or income verbally (e.g. '15 tl yemek' = 15 TRY food expense; "
            "'5000 tl maaş' = 5000 TRY salary income with is_income true). "
            "If they mention MULTIPLE items in one recording, put each in the \"expenses\" array. "
            "Transcribe their speech and extract fields for each item. "
            "Set is_income true for salary, payments received, refunds (maaş, gelir, kazanç, ödeme aldım). "
            "Detect the currency from context (₺/TL → TRY, $ → USD, € → EUR, £ → GBP). "
            "If no currency mentioned, use the user's likely local currency based on language. "
        )
        gemini_client = _get_gemini_client()
        if not gemini_client:
            logger.warning("parse-audio: Gemini client unavailable (GEMINI_API_KEY or google-genai)")
            return Response(
                {
                    "detail": "AI service is temporarily unavailable.",
                    "code": "GEMINI_CLIENT_UNAVAILABLE",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        parsed_any = _gemini_parse_media(audio_b64, mime_type, prompt, client=gemini_client)
        if parsed_any is None:
            logger.warning(
                "parse-audio: Gemini returned empty or invalid JSON (model=%s)",
                _gemini_model_id(),
            )
            return Response(
                {
                    "detail": "Could not analyze the voice recording.",
                    "code": "GEMINI_AUDIO_PARSE_FAILED",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        data = _build_batch_response(
            parsed_any,
            fallback_text="",
            receipt_url=None,
            expense_date_today=True,
        )
        return Response(data)


def _empty_insight_markdown(language: str) -> str:
    """Gemini çağırmadan dönemde veri yok mesajı (kullanıcı diline yakın)."""
    lang = (language or "en").split("-")[0].lower()[:5]
    lines = {
        "tr": (
            "## Bu aralıkta veri yok\n"
            "- Seçtiğiniz tarihlerde ve listede kayıtlı harcama bulunamadı.\n"
            "- Tarih aralığını genişletmeyi veya **Tüm listeler** seçeneğini deneyin."
        ),
        "de": (
            "## Keine Ausgaben\n"
            "- In diesem Zeitraum/Liste gibt es keine Ausgaben.\n"
            "- Zeitraum vergrößern oder **Alle Listen** wählen."
        ),
        "fr": (
            "## Aucune dépense\n"
            "- Aucune dépense pour cette période ou cette liste.\n"
            "- Élargissez les dates ou choisissez **Toutes les listes**."
        ),
        "es": (
            "## Sin gastos\n"
            "- No hay gastos en este periodo o lista.\n"
            "- Amplía fechas o elige **Todas las listas**."
        ),
    }
    return lines.get(
        lang,
        "## No spending in this range\n"
        "- There are no expenses for the dates and list you picked.\n"
        "- Try a wider date range or **All lists**.",
    )


def _build_spending_summary_dict(qs) -> dict:
    """QuerySet üzerinde özet JSON (Gemini prompt)."""
    from django.db.models import Count, Sum

    total = qs.count()
    if total == 0:
        return {"expense_rows_in_range": 0}

    spend_qs = qs.filter(is_income=False)
    spend_count = spend_qs.count()
    income_qs = qs.filter(is_income=True)

    by_cat_currency = []
    for row in spend_qs.values("currency", "category").annotate(total=Sum("amount"), n=Count("id")):
        by_cat_currency.append(
            {
                "currency": row["currency"],
                "category": row["category"],
                "total": float(row["total"]),
                "count": row["n"],
            }
        )

    income_by_currency = []
    for row in income_qs.values("currency").annotate(total=Sum("amount")):
        income_by_currency.append({"currency": row["currency"], "total": float(row["total"])})

    samples = []
    for row in spend_qs.order_by("-date", "-id").values(
        "date", "amount", "currency", "category", "description"
    )[:48]:
        samples.append(
            {
                "date": row["date"].isoformat(),
                "amount": float(row["amount"]),
                "currency": row["currency"],
                "category": row["category"],
                "description": (row["description"] or "")[:80],
            }
        )

    return {
        "expense_rows_in_range": total,
        "spending_transactions": spend_count,
        "income_transactions": income_qs.count(),
        "totals_by_currency_and_category": by_cat_currency,
        "income_by_currency": income_by_currency,
        "recent_spending_sample": samples,
    }


def _gemini_spending_insight(summary_json: str, language: str) -> str | None:
    client = _get_gemini_client()
    if not client:
        return None
    lang_name = LANGUAGE_NAMES.get((language or "en")[:5], "English")
    prompt = (
        "You are a concise personal finance coach.\n"
        "You receive ONLY this JSON about the user's transactions in the chosen period "
        "(spending rows have is_income false in the DB; the JSON separates spending vs income counts "
        "and lists totals_by_currency_and_category for spending only).\n"
        f"{summary_json}\n\n"
        f"Write your answer in {lang_name} only.\n"
        "Use short markdown: a single ## title line, then 4–8 bullet lines starting with '- '. "
        "Highlight patterns, one or two realistic suggestions, and optional cautions. "
        "Do not invent numbers; only use values from the JSON. "
        "Do not output JSON or fenced code blocks; plain markdown text only.\n"
    )
    try:
        resp = client.models.generate_content(
            model=_gemini_model_id(),
            contents=prompt,
        )
        raw = _extract_generate_content_text(resp)
        return raw.strip() if raw else None
    except Exception:
        logger.exception("gemini spending insights failed model=%s", _gemini_model_id())
        return None


class SpendingInsightsView(APIView):
    """Seçilen dönem + listedeki harcamaları Gemini ile özet tavsiyeye çevirir."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from expenses.models import Expense, ExpenseList

        ser = SpendingInsightsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        start = ser.validated_data["start_date"]
        end = ser.validated_data["end_date"]
        list_id = ser.validated_data.get("list_id")
        language = ser.validated_data.get("language") or "en"

        if end < start:
            return Response(
                {"detail": "End date must be on or after the start date."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if (end - start).days > 366:
            return Response(
                {"detail": "Date range cannot exceed 366 days."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = Expense.objects.filter(user=request.user, date__gte=start, date__lte=end)
        if list_id is not None:
            if not ExpenseList.objects.filter(pk=list_id, user=request.user).exists():
                return Response(
                    {"list_id": ["Invalid list for this user."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            qs = qs.filter(expense_list_id=list_id)

        summary = _build_spending_summary_dict(qs)
        count = int(summary.get("expense_rows_in_range") or 0)
        if count == 0:
            return Response(
                {
                    "insight": _empty_insight_markdown(language),
                    "expense_count": 0,
                    "summary": summary,
                }
            )

        if summary.get("spending_transactions", 0) == 0 and summary.get("income_transactions", 0) > 0:
            # Sadece gelir satırları
            return Response(
                {
                    "insight": _empty_insight_markdown(language),
                    "expense_count": count,
                    "summary": summary,
                }
            )

        summary_json = json.dumps(summary, ensure_ascii=False)
        if len(summary_json) > 24000:
            summary_json = summary_json[:24000] + "\n…(truncated)"

        insight = _gemini_spending_insight(summary_json, language)
        if insight is None:
            client = _get_gemini_client()
            if not client:
                logger.warning("spending-insights: Gemini client unavailable")
                return Response(
                    {
                        "detail": "AI service is temporarily unavailable.",
                        "code": "GEMINI_CLIENT_UNAVAILABLE",
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            logger.warning("spending-insights: Gemini returned no insight")
            return Response(
                {
                    "detail": "Could not generate insights.",
                    "code": "GEMINI_INSIGHTS_FAILED",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "insight": insight,
                "expense_count": count,
                "summary": summary,
            }
        )
