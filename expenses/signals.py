from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ExpenseList


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_expense_list(sender, instance, created, **kwargs):
    if created:
        ExpenseList.objects.create(user=instance, name="Private list", is_default=True)
