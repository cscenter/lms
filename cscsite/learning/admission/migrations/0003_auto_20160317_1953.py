# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0002_auto_20160317_1832'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applicant',
            name='course',
            field=models.CharField(help_text='Applicant|course', max_length=355, verbose_name='Course'),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='experience',
            field=models.TextField(help_text='Applicant|work_or_study_experience', verbose_name='Experience'),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='faculty',
            field=models.TextField(help_text='Applicant|faculty', verbose_name='Faculty'),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='graduate_work',
            field=models.TextField(help_text='Applicant|graduate_work_or_dissertation', null=True, verbose_name='Graduate work', blank=True),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='motivation',
            field=models.TextField(help_text='Applicant|motivation_why', verbose_name='Your motivation'),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='phone',
            field=models.CharField(help_text='Applicant|phone', max_length=42, verbose_name='Contact phone'),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='preferred_study_programs',
            field=models.CharField(help_text='Applicant|study_program', max_length=255, verbose_name='Study program'),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='where_did_you_learn',
            field=models.TextField(help_text='Applicant|where_did_you_learn', verbose_name='Where did you learn?'),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='your_future_plans',
            field=models.TextField(help_text='Applicant|future_plans', null=True, verbose_name='Future plans', blank=True),
        ),
    ]
