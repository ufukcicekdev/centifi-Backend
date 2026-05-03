"""Send one test message: `python manage.py smtp2go_test you@example.com`"""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string

from core.email_branding import attach_centifi_logo_inline_if_needed, wrap_branded_email_html


class Command(BaseCommand):
    help = "Send a branded HTML test email (uses SMTP2GO API if configured, else EMAIL_* SMTP)."

    def add_arguments(self, parser):
        parser.add_argument(
            "to",
            nargs="?",
            default="ufukcicek199@gmail.com",
            help="Recipient email address",
        )

    def handle(self, *args, **options):
        to = (options["to"] or "").strip()
        if not to:
            self.stderr.write(self.style.ERROR("Missing recipient."))
            return
        self.stdout.write(f"BACKEND={settings.EMAIL_BACKEND} FROM={settings.DEFAULT_FROM_EMAIL!r} -> {to}")
        subject = "Centifi — SMTP2GO test"
        plain = "If you read this, outbound email from the Centifi backend is working."
        inner = render_to_string("tests/smtp_inner.html", {})
        html = wrap_branded_email_html(
            inner_html=inner,
            document_title=subject,
            header_subtitle="Mail delivery check",
            preheader="Centifi test — logo and layout preview.",
        )
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain,
            from_email=None,
            to=[to],
        )
        msg.attach_alternative(html, "text/html")
        attach_centifi_logo_inline_if_needed(msg)
        msg.send(fail_silently=False)
        self.stdout.write(self.style.SUCCESS("OK: message handed off to email backend."))
