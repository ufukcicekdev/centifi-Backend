from django.contrib import admin
from django.urls import path, include

from core.views import app_password_reset_bridge, health

urlpatterns = [
    path("health", health),
    path("health/", health, name="health"),
    path("open/reset-password/", app_password_reset_bridge, name="app_password_reset_bridge"),
    path("admin/", admin.site.urls),
    path("api/users/", include("users.urls")),
    path("api/bank-apps/", include("users.bank_urls")),
    path("api/expenses/", include("expenses.urls")),
    path("api/recurring-expenses/", include("expenses.recurring_urls")),
    path("api/expense-lists/", include("expenses.list_urls")),
    path("api/custom-categories/", include("expenses.category_urls")),
    path("api/ai/", include("ai.urls")),
]
