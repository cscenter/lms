# -*- coding: utf-8 -*-
# Generated by Django 1.9.12 on 2017-02-21 13:04
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_auto_20160318_1936'),
        ('learning', '0033_auto_20170220_2010'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudyProgram',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='StudyProgram|Name')),
                ('year', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1990)], verbose_name='Year')),
                ('description', models.TextField(help_text='How to style text read <a href="/commenting-the-right-way/" target="_blank">here</a>. Partially HTML is enabled too.', verbose_name='StudyProgram|description')),
                ('area', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='learning.AreaOfStudy', verbose_name='Area of Study')),
                ('city', models.ForeignKey(default='RU SPB', on_delete=django.db.models.deletion.CASCADE, to='core.City')),
            ],
            options={
                'verbose_name_plural': 'Study Programs',
                'verbose_name': 'Study Program',
            },
        ),
        migrations.CreateModel(
            name='StudyProgramCourse',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group', models.PositiveSmallIntegerField(verbose_name='Group')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='learning.Course', verbose_name='Course')),
                ('study_program', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='learning.StudyProgram', verbose_name='Study Program')),
            ],
            options={
                'verbose_name_plural': 'Study Program Courses',
                'verbose_name': 'Study Program Course',
            },
        ),
    ]
