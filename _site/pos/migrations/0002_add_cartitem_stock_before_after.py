# Generated manually for CartItem stock_before/stock_after

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartitem',
            name='stock_before',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cartitem',
            name='stock_after',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
