import json
import logging
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .serializers import UserSerializer
from .subscription_rc import (
    ENTITLEMENT_PRO,
    fetch_revenuecat_subscriber_json,
    update_user_pro_expiry,
)

logger = logging.getLogger(__name__)


class RevenueCatWebhookView(APIView):
    """
    RevenueCat → Project settings → Webhooks.
    Authorization: Bearer <REVENUECAT_WEBHOOK_SECRET>
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def post(self, request):
        secret = (getattr(settings, "REVENUECAT_WEBHOOK_SECRET", None) or "").strip()
        if not secret:
            logger.warning("revenuecat_webhook: REVENUECAT_WEBHOOK_SECRET not set — rejecting")
            return Response({"detail": "Webhook not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        auth = (request.headers.get("Authorization") or "").strip()
        if auth != f"Bearer {secret}":
            return Response({"detail": "Unauthorized."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            body = request.data if isinstance(request.data, dict) else {}
        except Exception:
            body = {}
        if not body and request.body:
            try:
                body = json.loads(request.body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                body = {}

        event = body.get("event") if isinstance(body, dict) else None
        if not isinstance(event, dict):
            return Response({"ok": True}, status=status.HTTP_200_OK)

        app_user_id = event.get("app_user_id")
        if app_user_id is None or not str(app_user_id).isdigit():
            return Response({"ok": True}, status=status.HTTP_200_OK)

        try:
            user = User.objects.get(pk=int(str(app_user_id)))
        except (User.DoesNotExist, ValueError):
            return Response({"ok": True}, status=status.HTTP_200_OK)

        subscriber = event.get("subscriber")
        if isinstance(subscriber, dict):
            update_user_pro_expiry(user, subscriber)
        else:
            # Minimal event: use expiration_at_ms when entitlement includes pro
            exp_ms = event.get("expiration_at_ms")
            ent_ids = event.get("entitlement_ids") or []
            ev_type = (event.get("type") or "").upper()
            if exp_ms and ENTITLEMENT_PRO in ent_ids:
                user.pro_entitlement_expires_at = datetime.fromtimestamp(
                    float(exp_ms) / 1000.0,
                    tz=dt_timezone.utc,
                )
                user.save(update_fields=["pro_entitlement_expires_at"])
            elif ev_type in ("EXPIRATION", "BILLING_ISSUE", "SUBSCRIPTION_PAUSED") and ENTITLEMENT_PRO not in ent_ids:
                user.pro_entitlement_expires_at = None
                user.save(update_fields=["pro_entitlement_expires_at"])

        return Response({"ok": True}, status=status.HTTP_200_OK)


class SubscriptionSyncView(APIView):
    """
    POST /api/users/subscription/sync/
    Pulls subscriber from RevenueCat REST API and updates ``pro_entitlement_expires_at``.
    Call after purchase / restore (webhook may be slightly delayed).
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        uid = str(request.user.pk)
        payload = fetch_revenuecat_subscriber_json(uid)
        if payload is None:
            return Response(
                {"detail": "RevenueCat API not configured or request failed."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        update_user_pro_expiry(request.user, payload)
        request.user.refresh_from_db()
        return Response(UserSerializer(request.user, context={"request": request}).data)
