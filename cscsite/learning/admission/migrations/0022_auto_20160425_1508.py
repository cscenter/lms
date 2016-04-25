# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0021_auto_20160425_1242'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='exam_max_score',
            field=models.SmallIntegerField(default=0, verbose_name='Campaign|Exam_max_score'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='campaign',
            name='exam_passing_score',
            field=models.SmallIntegerField(default=0, verbose_name='Campaign|Exam_passing_score'),
            preserve_default=False,
        ),
    ]
