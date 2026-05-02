from django.urls import path
from .views import ParseTextView, ParseImageView, ParseAudioView

urlpatterns = [
    path("parse-text/", ParseTextView.as_view(), name="parse_text"),
    path("parse-image/", ParseImageView.as_view(), name="parse_image"),
    path("parse-audio/", ParseAudioView.as_view(), name="parse_audio"),
]

