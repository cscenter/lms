# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0011_interview_interviewers'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applicant',
            name='experience',
            field=models.TextField(help_text='Applicant|work_or_study_experience', null=True, verbose_name='Experience', blank=True),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='where_did_you_learn',
            field=models.TextField(help_text='Applicant|where_did_you_learn_about_cs_center', verbose_name='Where did you learn?'),
        ),
    ]
