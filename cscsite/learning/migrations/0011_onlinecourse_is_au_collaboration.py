# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0010_auto_20150805_1746'),
    ]

    operations = [
        migrations.AddField(
            model_name='onlinecourse',
            name='is_au_collaboration',
            field=models.BooleanField(default=False, verbose_name='Published in video section'),
        ),
    ]
