# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='applicant',
            options={'verbose_name': 'Applicant', 'verbose_name_plural': 'Applicants'},
        ),
        migrations.AlterModelOptions(
            name='campaign',
            options={'verbose_name': 'Campaign', 'verbose_name_plural': 'Campaigns'},
        ),
        migrations.AlterModelOptions(
            name='comment',
            options={'verbose_name': 'Comment', 'verbose_name_plural': 'Comments'},
        ),
        migrations.AlterModelOptions(
            name='exam',
            options={'verbose_name': 'Exam', 'verbose_name_plural': 'Exams'},
        ),
        migrations.AlterModelOptions(
            name='interview',
            options={'verbose_name': 'Interview', 'verbose_name_plural': 'Interviews'},
        ),
        migrations.AlterModelOptions(
            name='interviewer',
            options={'verbose_name': 'Interviewer', 'verbose_name_plural': 'Interviewers'},
        ),
        migrations.AlterModelOptions(
            name='test',
            options={'verbose_name': 'Testing', 'verbose_name_plural': 'Testings'},
        ),
        migrations.AddField(
            model_name='applicant',
            name='github_id',
            field=models.CharField(help_text='Applicant|github_id', max_length=255, null=True, verbose_name='Github ID', blank=True),
        ),
        migrations.AddField(
            model_name='applicant',
            name='has_job',
            field=models.NullBooleanField(help_text='Applicant|has_job', verbose_name='Do you work?'),
        ),
        migrations.AddField(
            model_name='applicant',
            name='position',
            field=models.CharField(help_text='Applicant|position', max_length=255, null=True, verbose_name='Position', blank=True),
        ),
        migrations.AddField(
            model_name='applicant',
            name='workplace',
            field=models.CharField(help_text='Applicant|workplace', max_length=255, null=True, verbose_name='Workplace', blank=True),
        ),
        migrations.AddField(
            model_name='applicant',
            name='your_future_plans',
            field=models.CharField(help_text='Applicant|future_plans', max_length=255, null=True, verbose_name='Future plans', blank=True),
        ),
    ]
