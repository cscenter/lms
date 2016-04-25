# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import learning.admission.models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0022_auto_20160425_1508'),
    ]

    operations = [
        migrations.CreateModel(
            name='Contest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('contest_id', models.CharField(help_text='Applicant|yandex_contest_id', max_length=42, null=True, verbose_name='Contest #ID', blank=True)),
                ('file', models.FileField(upload_to=learning.admission.models.contest_assignments_upload_to, verbose_name='Assignments in pdf format', blank=True)),
            ],
            options={
                'verbose_name': 'Contest',
                'verbose_name_plural': 'Contests',
            },
        ),
        migrations.CreateModel(
            name='InterviewAssignments',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='InterviewAssignments|name')),
                ('description', models.TextField(help_text='TeX support', verbose_name='Assignment description')),
                ('campaign', models.ForeignKey(related_name='interview_assignments', on_delete=django.db.models.deletion.PROTECT, verbose_name='InterviewAssignments|Campaign', to='admission.Campaign')),
            ],
        ),
    ]
