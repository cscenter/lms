# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0013_studentassignment_last_comment_from'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseoffering',
            name='grading_type',
            field=models.SmallIntegerField(default=0, verbose_name='CourseOffering|grading_type', choices=[(0, 'Default'), (1, 'Binary')]),
        ),
    ]
