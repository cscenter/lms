# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0012_auto_20160408_1239'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentassignment',
            name='last_comment_from',
            field=models.PositiveSmallIntegerField(default=0, help_text='System field. 0 - no comments yet. 1 - from student. 2 - from teacher', verbose_name='Last comment from', editable=False),
        ),
    ]
