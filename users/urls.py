from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .subscription_views import RevenueCatWebhookView, SubscriptionSyncView
from .password_views import ChangePasswordView, ForgotPasswordView, ResetPasswordView, VerifyPasswordResetCodeView
from .views import RegisterView, ProfileView, EmailOrUsernameTokenObtainPairView, SocialAuthView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", EmailOrUsernameTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("password/forgot/", ForgotPasswordView.as_view(), name="password_forgot"),
    path("password/verify-code/", VerifyPasswordResetCodeView.as_view(), name="password_verify_code"),
    path("password/reset/", ResetPasswordView.as_view(), name="password_reset"),
    path("password/change/", ChangePasswordView.as_view(), name="password_change"),
    path("me/", ProfileView.as_view(), name="profile"),
    path("social-auth/", SocialAuthView.as_view(), name="social_auth"),
    path("revenuecat-webhook/", RevenueCatWebhookView.as_view(), name="revenuecat_webhook"),
    path("subscription/sync/", SubscriptionSyncView.as_view(), name="subscription_sync"),
]
