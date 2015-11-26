# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0028_studentproject_migrate_data_from_student_to_students'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='studentproject',
            name='student',
        ),
        migrations.AlterField(
            model_name='studentproject',
            name='students',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL, verbose_name='Students'),
        ),
    ]
