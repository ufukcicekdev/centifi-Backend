from django.urls import path
from .views import ParseAudioView, ParseImageView, ParseTextView, SpendingInsightsView

urlpatterns = [
    path("parse-text/", ParseTextView.as_view(), name="parse_text"),
    path("parse-image/", ParseImageView.as_view(), name="parse_image"),
    path("parse-audio/", ParseAudioView.as_view(), name="parse_audio"),
    path("spending-insights/", SpendingInsightsView.as_view(), name="spending_insights"),
    path("receipt-upload-status/<str:request_id>/", ReceiptUploadStatusView.as_view(), name="receipt_upload_status"),
]

