# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0008_data_add_studyprograms_again'),
        ('users', '0002_auto_20150219_1929'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='studentinfo',
            name='online_courses',
        ),
        migrations.RemoveField(
            model_name='studentinfo',
            name='shad_courses',
        ),
        migrations.RemoveField(
            model_name='studentinfo',
            name='study_program',
        ),
        migrations.AddField(
            model_name='studentinfo',
            name='study_programs',
            field=models.ManyToManyField(to='learning.StudyProgram', verbose_name='StudentInfo|Study programs', blank=True),
            preserve_default=True,
        ),
    ]
