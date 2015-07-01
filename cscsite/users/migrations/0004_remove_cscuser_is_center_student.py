# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_auto_20150701_1659'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cscuser',
            name='is_center_student',
        ),
    ]
