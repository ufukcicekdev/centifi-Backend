from rest_framework import serializers

from .models import TestUserApplication


class SubmitTestUserSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    platform = serializers.ChoiceField(choices=TestUserApplication.Platform.choices)
    language = serializers.CharField(max_length=5, required=False, allow_blank=True, default="en")
    website = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def validate_language(self, value: str) -> str:
        lang = (value or "en").strip().lower()[:5]
        return lang or "en"
