# Generated by Django 2.2.10 on 2020-02-19 12:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0009_auto_20200213_1542'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentassignment',
            name='deleted_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
