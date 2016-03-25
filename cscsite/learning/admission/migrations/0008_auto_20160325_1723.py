# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0007_auto_20160325_1457'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicant',
            name='status',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='Applicant|Status', choices=[('rejected_test', 'Rejected by test'), ('rejected_exam', 'Rejected by exam'), ('rejected_interview', 'Rejected by interview'), ('accept', 'Accept'), ('volunteer', 'Volunteer')]),
        ),
        migrations.AlterField(
            model_name='interview',
            name='decision',
            field=models.CharField(default='waiting', max_length=15, verbose_name='Interview|Decision', choices=[('waiting', 'Waiting for interview'), ('canceled', 'Canceled'), ('accept', 'Accept'), ('decline', 'Decline'), ('volunteer', 'Volunteer')]),
        ),
    ]
