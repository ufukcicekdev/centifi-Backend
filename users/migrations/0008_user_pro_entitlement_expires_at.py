from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_userbankapp_icon_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="pro_entitlement_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
