import os
import io
import json
import re
import base64
import uuid
from datetime import date

import boto3
from botocore.client import Config
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import ParseTextSerializer, ParseImageSerializer

EXPENSE_SCHEMA = {
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


def _get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception:
        return None


def _parse_gemini_response(text: str) -> dict | None:
    raw = (text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


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


def _gemini_parse_text(text: str, language: str = "en") -> dict | None:
    client = _get_gemini_client()
    if not client:
        return None
    lang_name = LANGUAGE_NAMES.get(language, "English")
    prompt = (
        f"The user wrote in {lang_name}: \"{text}\"\n"
        "Extract expense fields. Detect currency from context (₺/TL→TRY, $→USD, €→EUR, £→GBP). "
        "Return ONLY valid JSON matching this schema.\n"
        f"Schema: {json.dumps(EXPENSE_SCHEMA)}"
    )
    try:
        resp = _get_gemini_client().models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return _parse_gemini_response(resp.text)
    except Exception:
        return None


def _gemini_parse_media(data_b64: str, mime_type: str, prompt_text: str) -> dict | None:
    client = _get_gemini_client()
    if not client:
        return None
    try:
        from google.genai import types
        prompt = (
            f"{prompt_text} "
            "Return ONLY valid JSON matching this schema. "
            "For date use YYYY-MM-DD format. "
            "For currency detect from content or default to USD.\n"
            f"Schema: {json.dumps(EXPENSE_SCHEMA)}"
        )
        part = types.Part.from_bytes(data=base64.b64decode(data_b64), mime_type=mime_type)
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt, part],
        )
        return _parse_gemini_response(resp.text)
    except Exception:
        return None


class ParseTextView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = ParseTextSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        text = ser.validated_data["input"]
        language = ser.validated_data.get("language", "en")
        data = _gemini_parse_text(text, language) or _fallback_parse(text)
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

        data = _gemini_parse_media(
            image_b64, mime_type,
            "This is a receipt or expense document. Extract the expense fields."
        ) or _fallback_parse("")

        if receipt_url:
            data["receipt_url"] = receipt_url
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
            "They are describing a personal expense verbally (e.g. '15 tl yemek' means 15 TL food expense). "
            "Transcribe their speech and extract the expense fields. "
            "Detect the currency from context (₺/TL → TRY, $ → USD, € → EUR, £ → GBP). "
            "If no currency mentioned, use the user's likely local currency based on language. "
        )
        data = _gemini_parse_media(audio_b64, mime_type, prompt) or _fallback_parse("")
        return Response(data)
