# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0008_auto_20160329_1746'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assignment',
            name='notify_teachers',
            field=models.ManyToManyField(help_text='Leave blank if you want populate teachers from course offering settings', to='learning.CourseOfferingTeacher', verbose_name='Assignment|notify_settings', blank=True),
        ),
    ]
