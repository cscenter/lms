# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('learning', '0032_remove_courseoffering_teachers'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='courseoffering',
            name='teachers2',
        ),
        migrations.AddField(
            model_name='courseoffering',
            name='teachers',
            field=models.ManyToManyField(related_name='teaching_set', verbose_name='Course|teachers', through='learning.CourseOfferingTeacher', to=settings.AUTH_USER_MODEL),
        ),
    ]
