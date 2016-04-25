# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0023_contest_interviewassignments'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='interviewassignments',
            options={'verbose_name': 'Interview assignment', 'verbose_name_plural': 'Interview assignments'},
        ),
        migrations.AddField(
            model_name='contest',
            name='campaign',
            field=models.ForeignKey(related_name='contests', on_delete=django.db.models.deletion.PROTECT, default=0, verbose_name='Contest|Campaign', to='admission.Campaign'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='applicant',
            name='status',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='Applicant|Status', choices=[('rejected_cheating', 'Cheating'), ('rejected_test', 'Rejected by test'), ('rejected_exam', 'Rejected by exam'), ('rejected_interview', 'Rejected by interview'), ('accept', 'Accept'), ('volunteer', 'Applicant|Volunteer')]),
        ),
    ]
