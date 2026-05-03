from rest_framework import serializers


class ParseTextSerializer(serializers.Serializer):
    input = serializers.CharField(max_length=2000)
    language = serializers.CharField(default="en", max_length=5)


class ParseImageSerializer(serializers.Serializer):
    image = serializers.CharField()  # base64 encoded
    mime_type = serializers.CharField(default="image/jpeg")
    language = serializers.CharField(default="en", max_length=5)


class ParseResultSerializer(serializers.Serializer):
    amount = serializers.FloatField()
    description = serializers.CharField()
    category = serializers.CharField()
    date = serializers.CharField()
    currency = serializers.CharField()


class SpendingInsightsSerializer(serializers.Serializer):
    """POST /api/ai/spending-insights/ — Gemini ile dönem + isteğe bağlı liste özeti."""

    start_date = serializers.DateField()
    end_date = serializers.DateField()
    list_id = serializers.IntegerField(required=False, allow_null=True)
    language = serializers.CharField(default="en", max_length=5)

