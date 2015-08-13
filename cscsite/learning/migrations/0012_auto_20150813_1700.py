# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0011_onlinecourse_is_au_collaboration'),
    ]

    operations = [
        migrations.AlterField(
            model_name='onlinecourse',
            name='is_au_collaboration',
            field=models.BooleanField(default=False, verbose_name='Collaboration with AY'),
        ),
    ]
