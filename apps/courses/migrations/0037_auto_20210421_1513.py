# Generated by Django 3.1.7 on 2021-04-21 15:13

import core.db.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0036_assignment_time_zone'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assignment',
            name='time_zone',
            field=core.db.fields.TimeZoneField(default='Europe/Moscow', verbose_name='Time Zone'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='courseclass',
            name='time_zone',
            field=core.db.fields.TimeZoneField(default='Europe/Moscow', verbose_name='Time Zone'),
            preserve_default=False,
        ),
    ]
