from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0011_testuserapplication"),
    ]

    operations = [
        migrations.AddField(
            model_name="testuserapplication",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("invited", "Invited"),
                    ("rejected", "Rejected"),
                ],
                default="pending",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="testuserapplication",
            name="admin_notes",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="testuserapplication",
            name="invited_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
