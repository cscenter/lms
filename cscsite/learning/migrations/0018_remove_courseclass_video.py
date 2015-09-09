# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0017_other_materials'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='courseclass',
            name='video',
        ),
    ]
