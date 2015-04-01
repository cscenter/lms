# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0011_auto_20150401_1802'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='studentproject',
            name='semesters',
        ),
    ]
