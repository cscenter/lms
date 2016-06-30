# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0015_auto_20160615_1415'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseoffering',
            name='capacity',
            field=models.PositiveSmallIntegerField(default=0, help_text='0 - unlimited', verbose_name='CourseOffering|capacity'),
        ),
    ]
