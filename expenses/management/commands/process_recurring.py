from django.core.management.base import BaseCommand

from expenses.recurring_service import process_due_recurring


class Command(BaseCommand):
    help = "Vadesi gelen tekrarlayan masrafları işler (Celery yoksa cron ile çalıştırın)."

    def handle(self, *args, **options):
        stats = process_due_recurring()
        self.stdout.write(self.style.SUCCESS(str(stats)))
