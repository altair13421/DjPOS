import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_backfill_default_organization"),
    ]

    operations = [
        migrations.AlterField(
            model_name="settings",
            name="organization",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="settings",
                to="users.organization",
            ),
        ),
        migrations.AlterField(
            model_name="userlog",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="user_logs",
                to="users.organization",
            ),
        ),
    ]
