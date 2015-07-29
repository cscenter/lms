# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0004_auto_20150724_1656'),
    ]

    operations = [
        migrations.DeleteModel(
            name='City',
        ),
    ]
