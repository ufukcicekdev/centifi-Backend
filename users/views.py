import json
import urllib.request

from django.contrib.auth import authenticate
from rest_framework import generics, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User, UserBankApp
from .play_store_lookup import fetch_play_store_meta, package_name_from_store_url
from .password_email_copy import normalize_email_language
from .serializers import RegisterSerializer, UserSerializer, SocialAuthSerializer, UserBankAppSerializer


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


class ProfileView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserBankAppViewSet(viewsets.ModelViewSet):
    serializer_class = UserBankAppSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return UserBankApp.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="play-store-lookup")
    def play_store_lookup(self, request):
        """GET ?package=com.foo or ?store_url=https://play.google.com/...id=com.foo"""
        pkg = (request.query_params.get("package") or "").strip()
        store_url = (request.query_params.get("store_url") or "").strip()
        if not pkg and store_url:
            pkg = package_name_from_store_url(store_url)
        if not pkg:
            return Response(
                {"detail": "Provide package= or a Play Store store_url containing id=."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        name, icon_url = fetch_play_store_meta(pkg)
        return Response(
            {
                "package_name": pkg,
                "name": name,
                "icon_url": icon_url,
            }
        )


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
        language_pref = (ser.validated_data.get("language") or "").strip()

        if provider == "google":
            payload = self._verify_google(token)
            if not payload:
                return Response({"detail": "Invalid Google token."}, status=status.HTTP_401_UNAUTHORIZED)
            social_id = payload.get("sub", "")
            email = email or payload.get("email", "")
            name = name or payload.get("name", "")
            user = self._get_or_create(social_id, email, name, "google", language_pref=language_pref)

        elif provider == "apple":
            payload = self._verify_apple(token)
            if not payload:
                return Response({"detail": "Invalid Apple token."}, status=status.HTTP_401_UNAUTHORIZED)
            social_id = payload.get("sub", "")
            email = email or payload.get("email", "")
            user = self._get_or_create(social_id, email, name, "apple", language_pref=language_pref)

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
        """Decode Apple identity JWT payload (iss/sub); signature verify TODO for hardening."""
        try:
            import base64

            token = (identity_token or "").strip()
            parts = token.split(".")
            if len(parts) != 3:
                return None
            payload_b64 = parts[1]
            pad = (4 - len(payload_b64) % 4) % 4
            payload = json.loads(base64.urlsafe_b64decode(payload_b64 + ("=" * pad)))
            if payload.get("iss") != "https://appleid.apple.com":
                return None
            if not payload.get("sub"):
                return None
            return payload
        except Exception:
            return None

    # ── shared ────────────────────────────────────────────────────────────────

    def _get_or_create(self, social_id: str, email: str, name: str, provider: str, *, language_pref: str = "") -> User:
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

        lang = normalize_email_language(language_pref) if language_pref else "en"
        user = User.objects.create_user(
            username=username, email=email or "",
            first_name=first, last_name=last,
            password=None,
            language=lang,
            **{id_field: social_id},
        )
        if not user.has_usable_password():
            user.set_unusable_password()
            user.save(update_fields=["password"])
        return user
