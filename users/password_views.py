"""Forgot / reset password (email link) and authenticated password change."""

from __future__ import annotations

import logging

from django.contrib.auth import password_validation
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .password_email import send_password_reset_email
from .serializers import ChangePasswordSerializer, ForgotPasswordSerializer, ResetPasswordSerializer

logger = logging.getLogger(__name__)
_token_generator = PasswordResetTokenGenerator()


class ForgotPasswordView(APIView):
    """POST { email } — always 200 with generic message (no account enumeration)."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = ForgotPasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()
        if user and user.email:
            ok = send_password_reset_email(user=user)
            if not ok:
                logger.error("Forgot password: email send failed for existing user email=%s", email[:3] + "***")
        return Response(
            {
                "detail": "If an account exists for this email, we sent password reset instructions.",
            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    """POST { uid, token, new_password } — set password when token is valid."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = ResetPasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        uid_b64 = ser.validated_data["uid"]
        token = ser.validated_data["token"]
        new_password = ser.validated_data["new_password"]
        try:
            uid = force_str(urlsafe_base64_decode(uid_b64))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            raise ValidationError({"detail": "Invalid or expired reset link."}) from None
        if not _token_generator.check_token(user, token):
            raise ValidationError({"detail": "Invalid or expired reset link."})
        try:
            password_validation.validate_password(new_password, user)
        except Exception as e:
            raise ValidationError({"new_password": list(getattr(e, "messages", [str(e)]))}) from e
        user.set_password(new_password)
        user.save(update_fields=["password"])
        return Response({"detail": "Password has been reset. You can sign in with your new password."})


class ChangePasswordView(APIView):
    """POST { old_password?, new_password } — authenticated; old_password required if account has a usable password."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = ChangePasswordSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        user = request.user
        new_password = ser.validated_data["new_password"]
        old_password = ser.validated_data.get("old_password") or ""
        if user.has_usable_password():
            if not old_password or not user.check_password(old_password):
                raise ValidationError({"old_password": ["Current password is incorrect."]})
        try:
            password_validation.validate_password(new_password, user)
        except Exception as e:
            raise ValidationError({"new_password": list(getattr(e, "messages", [str(e)]))}) from e
        user.set_password(new_password)
        user.save(update_fields=["password"])
        return Response({"detail": "Password updated."})
