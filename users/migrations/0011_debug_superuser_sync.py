from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0010_alter_userlog_reason"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="allow_debug_superusers",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Copy active global superusers without organization memberships "
                    "to this organization's terminals for debugging, including their "
                    "password hashes."
                ),
            ),
        ),
        migrations.AddField(
            model_name="organizationmembership",
            name="is_debug_access",
            field=models.BooleanField(default=False),
        ),
    ]
