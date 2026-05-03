from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import UserBankAppViewSet

router = DefaultRouter()
router.register("", UserBankAppViewSet, basename="user-bank-app")

urlpatterns = [
    path("", include(router.urls)),
]
