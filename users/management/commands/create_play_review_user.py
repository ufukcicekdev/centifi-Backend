from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Create or reset a store review test user (email/password). Use for Play / App Store review accounts."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Login email for the review user.")
        parser.add_argument("--password", required=True, help="Password to set/reset.")
        parser.add_argument("--language", default="en", help="User language (default: en).")
        parser.add_argument(
            "--username",
            default="",
            help="Optional username override. Defaults to the email local-part.",
        )
        parser.add_argument(
            "--onboarding-completed",
            action="store_true",
            help="Set onboarding_completed=True (skip onboarding in app).",
        )
        parser.add_argument(
            "--pro-years",
            type=int,
            default=0,
            metavar="N",
            help="If >0, set pro_entitlement_expires_at to now+N years (API is_pro for review).",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        email = str(options["email"]).strip().lower()
        password = str(options["password"])
        language = (options.get("language") or "en").strip()[:5] or "en"
        username = (options.get("username") or "").strip()
        onboarding = bool(options.get("onboarding_completed"))
        pro_years = int(options.get("pro_years") or 0)

        if not username:
            username = email.split("@")[0]

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User(username=username, email=email, language=language)
            user.set_password(password)
            if onboarding:
                user.onboarding_completed = True
            if pro_years > 0:
                user.pro_entitlement_expires_at = timezone.now() + timedelta(days=365 * pro_years)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created review user: {email}"))
            return

        changed = False
        if user.username != username and not User.objects.exclude(pk=user.pk).filter(username=username).exists():
            user.username = username
            changed = True
        if getattr(user, "language", None) != language:
            user.language = language
            changed = True
        user.set_password(password)
        changed = True
        if onboarding and not user.onboarding_completed:
            user.onboarding_completed = True
            changed = True
        if pro_years > 0:
            user.pro_entitlement_expires_at = timezone.now() + timedelta(days=365 * pro_years)
            changed = True
        if changed:
            user.save()
        self.stdout.write(self.style.SUCCESS(f"Updated review user: {email}"))

