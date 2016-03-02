# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0008_courseoffering_enroll_before'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='courseoffering',
            name='enroll_before',
        ),
        migrations.AddField(
            model_name='semester',
            name='enroll_before',
            field=models.DateField(help_text='Students can enroll on or leave the course before this date (inclusive)', null=True, verbose_name='Enroll before', blank=True),
        ),
    ]
