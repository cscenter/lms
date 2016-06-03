# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0014_courseoffering_grading_type'),
        ('gallery', '0004_auto_20160602_1930'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='image',
            name='semester',
        ),
        migrations.AddField(
            model_name='image',
            name='course_offering',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Course offering', blank=True, to='learning.CourseOffering', null=True),
        ),
    ]
