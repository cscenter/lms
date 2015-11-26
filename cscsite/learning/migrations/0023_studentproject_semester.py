# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0022_courseoffering_survey_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentproject',
            name='semester',
            field=models.ForeignKey(related_name='semester_related', default=1, verbose_name='Semesters', to='learning.Semester'),
            preserve_default=False,
        ),
    ]
