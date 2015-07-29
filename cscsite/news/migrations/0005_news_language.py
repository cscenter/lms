# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0004_auto_20150729_1651'),
    ]

    operations = [
        migrations.AddField(
            model_name='news',
            name='language',
            field=models.CharField(default=b'ru', max_length=5, db_index=True, choices=[(b'ru', b'Russian'), (b'en', b'English')]),
        ),
    ]
