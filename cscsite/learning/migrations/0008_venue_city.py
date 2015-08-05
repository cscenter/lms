# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_auto_20150729_1623'),
        ('learning', '0007_auto_20150804_2016'),
    ]

    operations = [
        migrations.AddField(
            model_name='venue',
            name='city',
            field=models.ForeignKey(default=b'RU SPB', blank=True, to='core.City', null=True),
        ),
    ]
