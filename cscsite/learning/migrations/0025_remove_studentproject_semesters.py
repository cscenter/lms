# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0024_migrate_data_for_student_project_semester'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='studentproject',
            name='semesters',
        ),
        migrations.AlterField(
            model_name='studentproject',
            name='semester',
            field=models.ForeignKey(related_name='semester_related', verbose_name='Semester', to='learning.Semester'),
        ),
    ]
