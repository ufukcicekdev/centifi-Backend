from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0013_add_trial_started_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
