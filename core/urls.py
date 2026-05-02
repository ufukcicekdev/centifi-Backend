from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/", include("users.urls")),
    path("api/expenses/", include("expenses.urls")),
    path("api/expense-lists/", include("expenses.list_urls")),
    path("api/custom-categories/", include("expenses.category_urls")),
    path("api/ai/", include("ai.urls")),
]
