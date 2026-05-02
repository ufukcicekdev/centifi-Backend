from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import UserCustomCategoryViewSet

router = DefaultRouter()
router.register("", UserCustomCategoryViewSet, basename="user-custom-category")

urlpatterns = [
    path("", include(router.urls)),
]
