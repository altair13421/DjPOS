# Staged: add nullable organization FKs and reorder_level

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0001_initial"),
        ("inventory", "0006_alter_bundleitem_bundle_included_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="categories",
                to="organizations.organization",
            ),
        ),
        migrations.AddField(
            model_name="item",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="items",
                to="organizations.organization",
            ),
        ),
        migrations.AddField(
            model_name="item",
            name="reorder_level",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="bundle",
            name="organization",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="bundles",
                to="organizations.organization",
            ),
        ),
    ]
