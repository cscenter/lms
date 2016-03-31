# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0006_courseofferingteacher_notify_by_default'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignment',
            name='notify_settings',
            field=models.ManyToManyField(to='learning.CourseOfferingTeacher', verbose_name='Assignment|notify_settings', blank=True),
        ),
    ]
