"""Public test-user signup endpoint for the marketing site."""

from __future__ import annotations

from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .models import TestUserApplication
from .test_user_email import send_test_user_notification_email
from .test_user_serializers import SubmitTestUserSerializer

_SUCCESS = {
    "detail": "Thank you. We received your request and will be in touch.",
}

_DUPLICATE = {
    "code": "duplicate_email",
    "detail": "This email is already registered for the test program.",
}


class TestUserThrottle(AnonRateThrottle):
    rate = getattr(settings, "TEST_USERS_THROTTLE_RATE", "10/hour")


class SubmitTestUserView(APIView):
    """POST /api/test-users/ — save beta tester application."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [TestUserThrottle]

    def post(self, request):
        ser = SubmitTestUserSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        if (data.get("website") or "").strip():
            return Response(_SUCCESS, status=status.HTTP_200_OK)

        email = data["email"]
        if TestUserApplication.objects.filter(email=email).exists():
            return Response(_DUPLICATE, status=status.HTTP_409_CONFLICT)

        ua = (request.META.get("HTTP_USER_AGENT") or "")[:500]
        application = TestUserApplication.objects.create(
            email=email,
            platform=data["platform"],
            language=data.get("language") or "en",
            source="website",
            user_agent=ua,
        )
        send_test_user_notification_email(application=application)
        return Response(_SUCCESS, status=status.HTTP_201_CREATED)
