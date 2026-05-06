# Expense list optional emoji icon (user-created lists)

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0007_recurring_expense"),
    ]

    operations = [
        migrations.AddField(
            model_name="expenselist",
            name="emoji",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
    ]
