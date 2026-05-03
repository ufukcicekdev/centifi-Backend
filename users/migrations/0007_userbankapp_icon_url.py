from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_user_bank_app"),
    ]

    operations = [
        migrations.AddField(
            model_name="userbankapp",
            name="icon_url",
            field=models.URLField(blank=True, default="", max_length=500),
        ),
    ]
