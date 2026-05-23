from rest_framework import serializers

from .models import SiteFeedback


class SubmitFeedbackSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    message = serializers.CharField(min_length=10, max_length=5000, trim_whitespace=True)
    name = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    category = serializers.ChoiceField(
        choices=SiteFeedback.Category.choices,
        required=False,
        default=SiteFeedback.Category.GENERAL,
    )
    language = serializers.CharField(max_length=5, required=False, allow_blank=True, default="en")
    # Honeypot — must stay empty; bots often fill hidden fields.
    website = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_language(self, value: str) -> str:
        lang = (value or "en").strip().lower()[:5]
        return lang or "en"
