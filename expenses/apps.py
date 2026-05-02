from django.apps import AppConfig


class ExpensesConfig(AppConfig):
    name = "expenses"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        import expenses.signals  # noqa: F401
