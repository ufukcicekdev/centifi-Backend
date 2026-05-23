"""Public feedback endpoint for the marketing site."""

from __future__ import annotations

import logging

from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .feedback_email import send_feedback_notification_email
from .feedback_serializers import SubmitFeedbackSerializer
from .models import SiteFeedback

logger = logging.getLogger(__name__)

_SUCCESS = {
    "detail": "Thank you. Your message has been received.",
}


class FeedbackThrottle(AnonRateThrottle):
    rate = getattr(settings, "FEEDBACK_THROTTLE_RATE", "10/hour")


class SubmitFeedbackView(APIView):
    """POST /api/feedback/ — save feedback and email the team."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [FeedbackThrottle]

    def post(self, request):
        ser = SubmitFeedbackSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        if (data.get("website") or "").strip():
            return Response(_SUCCESS, status=status.HTTP_200_OK)

        ua = (request.META.get("HTTP_USER_AGENT") or "")[:500]
        feedback = SiteFeedback.objects.create(
            name=(data.get("name") or "").strip(),
            email=data["email"].strip().lower(),
            category=data.get("category") or SiteFeedback.Category.GENERAL,
            message=data["message"].strip(),
            language=data.get("language") or "en",
            source="website",
            user_agent=ua,
        )
        send_feedback_notification_email(feedback=feedback)
        return Response(_SUCCESS, status=status.HTTP_201_CREATED)
