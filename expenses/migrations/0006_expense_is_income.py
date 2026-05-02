from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0005_user_custom_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="expense",
            name="is_income",
            field=models.BooleanField(default=False),
        ),
    ]
