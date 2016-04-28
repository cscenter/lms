# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0025_auto_20160426_1340'),
    ]

    operations = [
        migrations.CreateModel(
            name='InterviewAssignment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='InterviewAssignments|name')),
                ('description', models.TextField(help_text='TeX support', verbose_name='Assignment description')),
                ('campaign', models.ForeignKey(related_name='interview_assignments', on_delete=django.db.models.deletion.PROTECT, verbose_name='InterviewAssignments|Campaign', to='admission.Campaign')),
            ],
            options={
                'verbose_name': 'Interview assignment',
                'verbose_name_plural': 'Interview assignments',
            },
        ),
        migrations.RemoveField(
            model_name='interviewassignments',
            name='campaign',
        ),
        migrations.DeleteModel(
            name='InterviewAssignments',
        ),
        migrations.AddField(
            model_name='interview',
            name='assignments',
            field=models.ManyToManyField(to='admission.InterviewAssignment', verbose_name='Interview|Interviewers'),
        ),
    ]
