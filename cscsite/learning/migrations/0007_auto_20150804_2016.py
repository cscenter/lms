# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_auto_20150729_1623'),
        ('learning', '0006_auto_20150804_1430'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseoffering',
            name='city',
            field=models.ForeignKey(default=b'RU SPB', blank=True, to='core.City', null=True),
        ),
        migrations.AddField(
            model_name='courseoffering',
            name='language',
            field=models.CharField(default=b'ru', max_length=5, db_index=True, choices=[(b'ru', b'Russian'), (b'en', b'English')]),
        ),
    ]
