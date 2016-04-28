# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0026_auto_20160427_1642'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='interviewer',
            name='campaign',
        ),
        migrations.RemoveField(
            model_name='interviewer',
            name='user',
        ),
        migrations.AlterField(
            model_name='comment',
            name='interviewer',
            field=models.ForeignKey(related_name='interview_comments', on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='interview',
            name='assignments',
            field=models.ManyToManyField(to='admission.InterviewAssignment', null=True, verbose_name='Interview|Assignments', blank=True),
        ),
        migrations.AlterField(
            model_name='interview',
            name='interviewers',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL, verbose_name='Interview|Interviewers'),
        ),
        migrations.DeleteModel(
            name='Interviewer',
        ),
    ]
