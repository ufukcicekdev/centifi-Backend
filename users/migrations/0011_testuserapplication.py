from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0010_sitefeedback"),
    ]

    operations = [
        migrations.CreateModel(
            name="TestUserApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254, unique=True)),
                (
                    "platform",
                    models.CharField(
                        choices=[("ios", "iOS"), ("android", "Android")],
                        max_length=10,
                    ),
                ),
                ("language", models.CharField(blank=True, default="en", max_length=5)),
                ("source", models.CharField(default="website", max_length=40)),
                ("user_agent", models.CharField(blank=True, default="", max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "test user application",
                "verbose_name_plural": "test user applications",
                "ordering": ["-created_at"],
            },
        ),
    ]
