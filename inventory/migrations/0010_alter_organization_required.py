import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0009_bundle_organization_category_organization_and_more"),
        ("users", "0003_backfill_default_organization"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bundle",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="bundles",
                to="users.organization",
            ),
        ),
        migrations.AlterField(
            model_name="category",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="categories",
                to="users.organization",
            ),
        ),
        migrations.AlterField(
            model_name="ingredientstock",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="ingredient_stock",
                to="users.organization",
            ),
        ),
        migrations.AlterField(
            model_name="item",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="items",
                to="users.organization",
            ),
        ),
        migrations.AlterField(
            model_name="stocklog",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="stock_logs",
                to="users.organization",
            ),
        ),
    ]
