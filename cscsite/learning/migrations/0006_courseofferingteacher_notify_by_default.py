# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0005_useful'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseofferingteacher',
            name='notify_by_default',
            field=models.BooleanField(default=False, help_text='Add teacher to assignment notify settings by default', verbose_name='Notify by default'),
        ),
    ]
