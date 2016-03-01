# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0007_auto_20160225_1423'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseoffering',
            name='enroll_before',
            field=models.DateField(help_text='Students can enroll on or leave the course before this date', null=True, verbose_name='Enroll before', blank=True),
        ),
    ]
