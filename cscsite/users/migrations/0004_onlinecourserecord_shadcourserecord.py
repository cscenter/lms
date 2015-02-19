# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import model_utils.fields
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_auto_20150219_1932'),
    ]

    operations = [
        migrations.CreateModel(
            name='OnlineCourseRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('name', models.CharField(max_length=255, verbose_name='Course|name')),
                ('student_info', models.ForeignKey(verbose_name='Student info record', to='users.StudentInfo')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Online course record',
                'verbose_name_plural': 'Online course records',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SHADCourseRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('name', models.CharField(max_length=255, verbose_name='Course|name')),
                ('grade', models.PositiveSmallIntegerField(blank=True, help_text='from 2 to 5, inclusive', null=True, verbose_name='Grade', validators=[django.core.validators.MinValueValidator(2), django.core.validators.MaxValueValidator(5)])),
                ('student_info', models.ForeignKey(verbose_name='Student info record', to='users.StudentInfo')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'SHAD course record',
                'verbose_name_plural': 'SHAD course records',
            },
            bases=(models.Model,),
        ),
    ]
