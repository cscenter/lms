# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0031_auto_20160429_1721'),
    ]

    operations = [
        migrations.AddField(
            model_name='interviewassignment',
            name='solution',
            field=models.TextField(help_text='TeX support', null=True, verbose_name='Assignment solution', blank=True),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='status',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='Applicant|Status', choices=[('rejected_test', 'Rejected by test'), ('rejected_exam', 'Rejected by exam'), ('rejected_cheating', 'Cheating'), ('interview_phase', 'Can be interviewed'), ('interview_assigned', 'Interview assigned'), ('rejected_interview', 'Rejected by interview'), ('accept', 'Accept'), ('volunteer', 'Applicant|Volunteer')]),
        ),
        migrations.AlterField(
            model_name='interview',
            name='decision',
            field=models.CharField(default='approval', max_length=15, verbose_name='Interview|Decision', choices=[('approval', 'Approval'), ('deferred', 'Deferred'), ('canceled', 'Canceled'), ('waiting', 'Waiting for interview'), ('accept', 'Accept'), ('decline', 'Decline'), ('volunteer', 'Volunteer')]),
        ),
    ]
