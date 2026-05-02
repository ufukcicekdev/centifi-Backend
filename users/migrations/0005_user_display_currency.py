from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_user_category_budgets"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="display_currency",
            field=models.CharField(default="USD", max_length=3),
        ),
    ]
