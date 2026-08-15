# Staged: add nullable organization FKs to POS models

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0001_initial"),
        ("pos", "0002_cartitem_bundle_unit_price_nullable_item"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="customers",
                to="organizations.organization",
            ),
        ),
        migrations.AddField(
            model_name="sale",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sales",
                to="organizations.organization",
            ),
        ),
    ]
