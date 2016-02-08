# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0003_auto_20160126_1544'),
    ]

    operations = [
        migrations.AddField(
            model_name='onlinecourse',
            name='is_self_paced',
            field=models.BooleanField(default=False, verbose_name='Without deadlines'),
        ),
    ]
