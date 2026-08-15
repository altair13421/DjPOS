# Finalize inventory organization ownership and integer quantities

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0002_backfill_default_organization"),
        ("inventory", "0007_add_organization_nullable"),
    ]

    operations = [
        migrations.AlterField(
            model_name="category",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="categories",
                to="organizations.organization",
            ),
        ),
        migrations.AlterField(
            model_name="item",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="items",
                to="organizations.organization",
            ),
        ),
        migrations.AlterField(
            model_name="bundle",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="bundles",
                to="organizations.organization",
            ),
        ),
        migrations.AlterField(
            model_name="item",
            name="quantity",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="bundleitem",
            name="quantity",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name="category",
            name="identifier",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="item",
            name="sku",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddConstraint(
            model_name="category",
            constraint=models.UniqueConstraint(
                fields=("organization", "identifier"),
                name="uniq_category_org_identifier",
            ),
        ),
        migrations.AddConstraint(
            model_name="item",
            constraint=models.UniqueConstraint(
                fields=("organization", "sku"),
                name="uniq_item_org_sku",
            ),
        ),
    ]
