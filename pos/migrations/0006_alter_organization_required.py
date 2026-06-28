import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pos", "0005_customer_organization_sale_created_by_and_more"),
        ("users", "0003_backfill_default_organization"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customer",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="customers",
                to="users.organization",
            ),
        ),
        migrations.AlterField(
            model_name="sale",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sales",
                to="users.organization",
            ),
        ),
    ]
