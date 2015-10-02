# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import learning.models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0019_assignmentstudent_last_commented'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseoffering',
            name='is_completed',
            field=models.BooleanField(default=False, verbose_name='Course already completed'),
        ),
        migrations.AlterField(
            model_name='assignmentattachment',
            name='attachment',
            field=models.FileField(upload_to=learning.models.assignmentattach_upload_to),
        ),
    ]
