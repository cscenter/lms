# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0009_data_add_cities'),
        ('users', '0008_remove_cscuser_study_programs'),
    ]

    operations = [
        migrations.AddField(
            model_name='cscuser',
            name='study_programs',
            field=models.ManyToManyField(to='learning.StudyProgram', verbose_name='StudentInfo|Study programs', blank=True),
            preserve_default=True,
        ),
    ]
