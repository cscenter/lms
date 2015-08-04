# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0008_auto_20150804_1430'),
    ]

    operations = [
        migrations.AlterField(
            model_name='news',
            name='city',
            field=models.ForeignKey(default=b'RU SPB', blank=True, to='core.City', null=True),
        ),
    ]
