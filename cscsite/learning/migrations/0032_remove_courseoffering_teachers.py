# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0031_auto_20151230_1158'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='courseoffering',
            name='teachers',
        ),
    ]
