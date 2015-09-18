# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0018_remove_courseclass_video'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignmentstudent',
            name='last_commented',
            field=models.DateTimeField(null=True, verbose_name='Last comment', blank=True),
        ),
    ]
