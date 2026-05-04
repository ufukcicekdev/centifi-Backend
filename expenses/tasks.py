from celery import shared_task


@shared_task(name="expenses.tasks.process_recurring_expenses")
def process_recurring_expenses() -> dict[str, int]:
    from expenses.recurring_service import process_due_recurring

    return process_due_recurring()
