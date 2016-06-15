# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0014_courseoffering_grading_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='studyprogram',
            name='name_en',
            field=models.CharField(max_length=255, null=True, verbose_name='StudyProgram|Name'),
        ),
        migrations.AddField(
            model_name='studyprogram',
            name='name_ru',
            field=models.CharField(max_length=255, null=True, verbose_name='StudyProgram|Name'),
        ),
    ]
