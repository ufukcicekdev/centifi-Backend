from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0009_passwordresetotp"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteFeedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(blank=True, default="", max_length=120)),
                ("email", models.EmailField(max_length=254)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("general", "General"),
                            ("bug", "Bug report"),
                            ("feature", "Feature request"),
                            ("billing", "Billing / subscription"),
                            ("other", "Other"),
                        ],
                        default="general",
                        max_length=20,
                    ),
                ),
                ("message", models.TextField()),
                ("language", models.CharField(blank=True, default="en", max_length=5)),
                ("source", models.CharField(default="website", max_length=40)),
                ("user_agent", models.CharField(blank=True, default="", max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "site feedback",
                "verbose_name_plural": "site feedback",
                "ordering": ["-created_at"],
            },
        ),
    ]
