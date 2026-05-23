from django.contrib import admin

from .models import SiteFeedback, TestUserApplication


@admin.register(SiteFeedback)
class SiteFeedbackAdmin(admin.ModelAdmin):
    list_display = ("created_at", "email", "name", "category", "language", "source")
    list_filter = ("category", "language", "source", "created_at")
    search_fields = ("email", "name", "message")
    readonly_fields = (
        "name",
        "email",
        "category",
        "message",
        "language",
        "source",
        "user_agent",
        "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False


@admin.register(TestUserApplication)
class TestUserApplicationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "email", "platform", "language", "source")
    list_filter = ("platform", "language", "source", "created_at")
    search_fields = ("email",)
    readonly_fields = ("email", "platform", "language", "source", "user_agent", "created_at")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False
