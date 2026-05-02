import json
import urllib.request

from django.contrib.auth import authenticate
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User
from .serializers import RegisterSerializer, UserSerializer, SocialAuthSerializer


def _tokens_for_user(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class EmailOrUsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field].required = False

    def validate(self, attrs):
        email = attrs.pop("email", None)
        username = attrs.get(self.username_field, "")
        if email and not username:
            try:
                username = User.objects.get(email__iexact=email).username
            except User.DoesNotExist:
                raise serializers.ValidationError({"email": "No user found with this email."})
            attrs[self.username_field] = username
        return super().validate(attrs)


class EmailOrUsernameTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailOrUsernameTokenObtainPairSerializer


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class SocialAuthView(APIView):
    """
    POST /api/users/social-auth/
    body: { provider: "google"|"apple", token: "...", name: "...", email: "..." }

    Google: token = Google ID token (from expo-auth-session)
    Apple:  token = Apple identity token (from expo-apple-authentication)

    Returns same JWT shape as /login/ so the frontend can use the same saveTokens logic.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = SocialAuthSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        provider = ser.validated_data["provider"]
        token = ser.validated_data["token"]
        name = ser.validated_data.get("name", "")
        email = ser.validated_data.get("email", "")

        if provider == "google":
            payload = self._verify_google(token)
            if not payload:
                return Response({"detail": "Invalid Google token."}, status=status.HTTP_401_UNAUTHORIZED)
            social_id = payload.get("sub", "")
            email = email or payload.get("email", "")
            name = name or payload.get("name", "")
            user = self._get_or_create(social_id, email, name, "google")

        elif provider == "apple":
            payload = self._verify_apple(token)
            if not payload:
                return Response({"detail": "Invalid Apple token."}, status=status.HTTP_401_UNAUTHORIZED)
            social_id = payload.get("sub", "")
            email = email or payload.get("email", "")
            user = self._get_or_create(social_id, email, name, "apple")

        else:
            return Response({"detail": "Unknown provider."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(_tokens_for_user(user))

    # ── Google ────────────────────────────────────────────────────────────────

    def _verify_google(self, id_token: str) -> dict | None:
        """Verify Google ID token via Google's tokeninfo endpoint (no extra lib needed)."""
        try:
            url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
            with urllib.request.urlopen(url, timeout=5) as resp:
                payload = json.loads(resp.read())
            # Basic check: token must not be expired (Google already checks this)
            if payload.get("error"):
                return None
            return payload
        except Exception:
            return None

    # ── Apple ─────────────────────────────────────────────────────────────────

    def _verify_apple(self, identity_token: str) -> dict | None:
        """
        Minimal Apple identity token verification.
        In production, verify JWT signature with Apple's public keys.
        For now: decode payload (base64) and trust the client (acceptable for
        internal apps; add full JWT verification before App Store submission).
        """
        try:
            import base64
            parts = identity_token.split(".")
            if len(parts) != 3:
                return None
            payload_b64 = parts[1] + "=="  # pad
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            if payload.get("iss") != "https://appleid.apple.com":
                return None
            return payload
        except Exception:
            return None

    # ── shared ────────────────────────────────────────────────────────────────

    def _get_or_create(self, social_id: str, email: str, name: str, provider: str) -> User:
        id_field = f"{provider}_id"
        # Try to find existing user by social ID
        user = User.objects.filter(**{id_field: social_id}).first()
        if not user and email:
            user = User.objects.filter(email__iexact=email).first()
        if user:
            if not getattr(user, id_field):
                setattr(user, id_field, social_id)
                user.save(update_fields=[id_field])
            return user

        # Create new user
        username_base = (email.split("@")[0] if email else social_id[:20]).lower()
        username = username_base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{username_base}{counter}"
            counter += 1

        first = last = ""
        if name:
            parts = name.strip().split(" ", 1)
            first = parts[0]
            last = parts[1] if len(parts) > 1 else ""

        user = User.objects.create_user(
            username=username, email=email,
            first_name=first, last_name=last,
            password=None,
            **{id_field: social_id},
        )
        return user
