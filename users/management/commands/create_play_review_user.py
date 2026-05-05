from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or reset a Play Console review test user (email/password)."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Login email for the review user.")
        parser.add_argument("--password", required=True, help="Password to set/reset.")
        parser.add_argument("--language", default="en", help="User language (default: en).")
        parser.add_argument(
            "--username",
            default="",
            help="Optional username override. Defaults to the email local-part.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        email = str(options["email"]).strip().lower()
        password = str(options["password"])
        language = (options.get("language") or "en").strip()[:5] or "en"
        username = (options.get("username") or "").strip()

        if not username:
            username = email.split("@")[0]

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User(username=username, email=email, language=language)
            user.set_password(password)
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
        if changed:
            user.save()
        self.stdout.write(self.style.SUCCESS(f"Updated review user: {email}"))

