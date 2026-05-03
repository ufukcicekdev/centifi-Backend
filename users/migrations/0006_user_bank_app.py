import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_user_display_currency"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserBankApp",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("emoji", models.CharField(default="🏦", max_length=16)),
                ("store_url", models.URLField(max_length=500)),
                (
                    "package_name",
                    models.CharField(
                        help_text="Android applicationId — used to filter notifications.",
                        max_length=200,
                    ),
                ),
                ("enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bank_apps",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.AddConstraint(
            model_name="userbankapp",
            constraint=models.UniqueConstraint(
                fields=("user", "package_name"),
                name="user_bank_app_unique_package_per_user",
            ),
        ),
    ]
