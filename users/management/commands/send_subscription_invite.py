"""
Broadcast the subscription-invite email to all (or filtered) users.

Usage examples:
    # Dry-run — just print what would be sent:
    python manage.py send_subscription_invite --dry-run

    # Send to everyone:
    python manage.py send_subscription_invite

    # Only users whose language is 'tr':
    python manage.py send_subscription_invite --lang tr

    # Only users who have NOT subscribed yet (requires is_premium / subscription_active field):
    python manage.py send_subscription_invite --non-premium-only

    # Limit & offset for batching:
    python manage.py send_subscription_invite --limit 500 --offset 0
"""

from __future__ import annotations

import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from core.email_branding import attach_centifi_logo_inline_if_needed, wrap_branded_email_html
from users.subscription_email_copy import subscription_email_context
from users.password_email_copy import normalize_email_language

User = get_user_model()


class Command(BaseCommand):
    help = "Send the subscription-invite email to users, respecting their preferred language."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Print recipients without sending.")
        parser.add_argument("--lang", type=str, default="", help="Filter by language code (e.g. 'tr').")
        parser.add_argument("--non-premium-only", action="store_true", help="Skip users who are already premium.")
        parser.add_argument("--limit", type=int, default=0, help="Max users to process (0 = all).")
        parser.add_argument("--offset", type=int, default=0, help="Skip the first N users.")
        parser.add_argument("--delay", type=float, default=0.1, help="Seconds to wait between sends (default 0.1).")

    def handle(self, *args, **options):
        qs = User.objects.filter(is_active=True).order_by("id")

        if options["lang"]:
            qs = qs.filter(language=normalize_email_language(options["lang"]))

        if options["non_premium_only"] and hasattr(User, "is_premium"):
            qs = qs.filter(is_premium=False)

        if options["offset"]:
            qs = qs[options["offset"]:]

        if options["limit"]:
            qs = qs[: options["limit"]]

        total = qs.count()
        self.stdout.write(f"Found {total} user(s) to process.")

        sent = skipped = errors = 0

        for user in qs.iterator():
            email = getattr(user, "email", "") or ""
            if not email:
                skipped += 1
                continue

            first_name = (getattr(user, "first_name", "") or "").strip()
            lang = normalize_email_language(getattr(user, "language", "en"))

            ctx = subscription_email_context(lang=lang, first_name=first_name)

            if options["dry_run"]:
                self.stdout.write(f"[DRY-RUN] Would send to {email} ({lang}) — {ctx['subject']}")
                sent += 1
                continue

            try:
                inner_html = render_to_string("subscription_inner.html", ctx)
                full_html = wrap_branded_email_html(
                    inner_html=inner_html,
                    document_title=ctx["subject"],
                    header_subtitle=ctx["header_subtitle"],
                    preheader=ctx["preheader"],
                    html_lang=lang,
                    footer_tagline=ctx["footer_tagline"],
                )
                msg = EmailMultiAlternatives(
                    subject=ctx["subject"],
                    body=ctx["plain_body"],
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email],
                )
                msg.attach_alternative(full_html, "text/html")
                attach_centifi_logo_inline_if_needed(msg)
                msg.send(fail_silently=False)
                self.stdout.write(self.style.SUCCESS(f"Sent → {email} ({lang})"))
                sent += 1
            except Exception as exc:  # noqa: BLE001
                self.stderr.write(self.style.ERROR(f"Error → {email}: {exc}"))
                errors += 1

            time.sleep(options["delay"])

        self.stdout.write(f"\nDone. sent={sent}  skipped={skipped}  errors={errors}")
