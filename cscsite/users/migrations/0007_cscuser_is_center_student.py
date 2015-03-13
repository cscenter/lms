# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_auto_20150219_2055'),
    ]

    operations = [
        migrations.AddField(
            model_name='cscuser',
            name='is_center_student',
            field=models.BooleanField(default=False, help_text='Students without this flag belong to CSClub only', verbose_name='Student of CSCenter'),
            preserve_default=True,
        ),
    ]
