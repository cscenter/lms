# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0009_data_add_cities'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseoffering',
            name='is_open',
            field=models.BooleanField(default=False, help_text='This course offering will be available on ComputerScience Club website so anyone can join', verbose_name='Open course offering'),
            preserve_default=True,
        ),
    ]
