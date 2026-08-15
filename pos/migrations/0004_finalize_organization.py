# Finalize POS organization ownership

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0002_backfill_default_organization"),
        ("pos", "0003_add_organization_nullable"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customer",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="customers",
                to="organizations.organization",
            ),
        ),
        migrations.AlterField(
            model_name="sale",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sales",
                to="organizations.organization",
            ),
        ),
    ]
