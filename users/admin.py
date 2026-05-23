from django.contrib import admin, messages
from django.utils import timezone

from .models import SiteFeedback, TestUserApplication
from .test_user_email import invite_url_for_application, send_test_user_invite_email


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


@admin.action(description="Send invite email (TestFlight / Play link from env)")
def send_test_user_invite(modeladmin, request, queryset):
    sent = 0
    failed: list[str] = []
    for application in queryset:
        ok, err = send_test_user_invite_email(application=application)
        if ok:
            application.status = TestUserApplication.Status.INVITED
            application.invited_at = timezone.now()
            application.save(update_fields=["status", "invited_at"])
            sent += 1
        else:
            failed.append(f"{application.email}: {err}")
    if sent:
        modeladmin.message_user(request, f"Invite email sent to {sent} applicant(s).", messages.SUCCESS)
    if failed:
        modeladmin.message_user(
            request,
            "Could not send: " + "; ".join(failed[:5]) + (" …" if len(failed) > 5 else ""),
            messages.ERROR,
        )


@admin.register(TestUserApplication)
class TestUserApplicationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "email", "platform", "status", "invited_at", "language")
    list_filter = ("status", "platform", "language", "created_at")
    search_fields = ("email", "admin_notes")
    readonly_fields = (
        "email",
        "platform",
        "language",
        "source",
        "user_agent",
        "created_at",
        "invited_at",
        "preview_invite_link",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "email",
                    "platform",
                    "status",
                    "language",
                    "preview_invite_link",
                    "invited_at",
                    "created_at",
                ),
            },
        ),
        (
            "Internal",
            {
                "fields": ("admin_notes", "source", "user_agent"),
            },
        ),
    )
    ordering = ("-created_at",)
    actions = [send_test_user_invite]

    @admin.display(description="Invite link (from env)")
    def preview_invite_link(self, obj: TestUserApplication) -> str:
        url = invite_url_for_application(obj)
        if not url:
            return "— Set TEST_USER_IOS_INVITE_URL or TEST_USER_ANDROID_INVITE_URL on the server —"
        return url

    def has_add_permission(self, request):
        return False
