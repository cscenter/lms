# Generated by Django 3.0.9 on 2020-09-10 10:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_auto_20200910_0909'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteconfiguration',
            name='default_branch_code',
            field=models.CharField(default='my', max_length=10, verbose_name='Branch code'),
            preserve_default=False,
        ),
    ]
