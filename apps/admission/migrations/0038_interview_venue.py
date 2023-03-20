# Generated by Django 3.1.12 on 2021-07-01 08:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0015_auto_20210413_1607"),
        ("admission", "0037_auto_20210629_1412"),
    ]

    operations = [
        migrations.AddField(
            model_name="interview",
            name="venue",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="core.location",
                verbose_name="Venue",
            ),
        ),
    ]
