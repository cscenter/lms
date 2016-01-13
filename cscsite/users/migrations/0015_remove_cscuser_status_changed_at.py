# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_auto_20160113_1840'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cscuser',
            name='status_changed_at',
        ),
    ]
