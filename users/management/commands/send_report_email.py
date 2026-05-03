"""Belirtilen hesaba harcama raporu e-postası gönder: ``python manage.py send_report_email user@mail.com``"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from expenses.report_email import send_expense_report_email


class Command(BaseCommand):
    help = "Send the branded expense report email to a user's registered address (by account email)."

    def add_arguments(self, parser):
        parser.add_argument(
            "email",
            help="User account email (must exist in DB; mail goes to this address)",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Report window length in days ending today (default: 90)",
        )

    def handle(self, *args, **options):
        email = (options["email"] or "").strip()
        days = max(1, min(int(options["days"] or 90), 366))
        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            self.stderr.write(self.style.ERROR(f"No user with email: {email}"))
            return
        end = date.today()
        start = end - timedelta(days=days)
        self.stdout.write(f"User id={user.pk} username={user.username!r} -> report {start} .. {end}")
        try:
            result = send_expense_report_email(user=user, start=start, end=end, list_id=None)
        except Exception as e:
            self.stderr.write(self.style.ERROR(str(e)))
            raise
        self.stdout.write(self.style.SUCCESS(str(result)))
