"""Forgot / reset password (email 6-digit code) and authenticated password change."""

from __future__ import annotations

import logging
import secrets
from datetime import timedelta

from django.contrib.auth import password_validation
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PasswordResetOTP, User
from .password_email import send_password_reset_otp_email
from .password_otp import generate_reset_code, hash_reset_code
from .serializers import ChangePasswordSerializer, ForgotPasswordSerializer, ResetPasswordSerializer

logger = logging.getLogger(__name__)

_OTP_TTL = timedelta(minutes=15)
_OTP_MAX_ATTEMPTS = 10
_RESET_INVALID_MSG = "Invalid or expired code. Request a new code from Forgot password."


class ForgotPasswordView(APIView):
    """POST { email } — always 200 with generic message (no account enumeration)."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = ForgotPasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()
        if user and user.email:
            plain = generate_reset_code()
            PasswordResetOTP.objects.filter(user=user).delete()
            PasswordResetOTP.objects.create(
                user=user,
                code_hash=hash_reset_code(user.pk, plain),
                expires_at=timezone.now() + _OTP_TTL,
            )
            ok = send_password_reset_otp_email(user=user, plain_code=plain)
            if not ok:
                logger.error("Forgot password: email send failed for existing user email=%s", email[:3] + "***")
        return Response(
            {
                "detail": "If an account exists for this email, we sent a 6-digit code. Enter it in the app to set a new password.",
            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    """POST { email, code, new_password } — set password when code is valid."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = ResetPasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"]
        code = ser.validated_data["code"]
        new_password = ser.validated_data["new_password"]
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise ValidationError({"detail": _RESET_INVALID_MSG})
        now = timezone.now()
        otp = (
            PasswordResetOTP.objects.filter(user=user, expires_at__gt=now)
            .order_by("-created_at")
            .first()
        )
        if not otp:
            raise ValidationError({"detail": _RESET_INVALID_MSG})
        expected = hash_reset_code(user.pk, code)
        if not secrets.compare_digest(otp.code_hash, expected):
            otp.attempts += 1
            if otp.attempts >= _OTP_MAX_ATTEMPTS:
                otp.delete()
                raise ValidationError(
                    {"detail": "Too many incorrect attempts. Request a new code from Forgot password."}
                )
            otp.save(update_fields=["attempts"])
            raise ValidationError({"detail": _RESET_INVALID_MSG})
        try:
            password_validation.validate_password(new_password, user)
        except Exception as e:
            raise ValidationError({"new_password": list(getattr(e, "messages", [str(e)]))}) from e
        user.set_password(new_password)
        user.save(update_fields=["password"])
        PasswordResetOTP.objects.filter(user=user).delete()
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
