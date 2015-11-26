# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0025_remove_studentproject_semesters'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentproject',
            name='semester',
            field=models.ForeignKey(verbose_name='Semester', to='learning.Semester'),
        ),
    ]
