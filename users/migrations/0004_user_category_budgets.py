from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_user_onboarding_completed"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="category_budgets",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="user",
            name="budget_alerts_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="user",
            name="budget_alert_threshold_percent",
            field=models.PositiveSmallIntegerField(default=90),
        ),
    ]
