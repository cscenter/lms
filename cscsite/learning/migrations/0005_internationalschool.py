# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0004_onlinecourse_is_self_paced'),
    ]

    operations = [
        migrations.CreateModel(
            name='InternationalSchool',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('start', models.DateTimeField(null=True, verbose_name='start', blank=True)),
                ('end', models.DateTimeField(null=True, verbose_name='end', blank=True)),
                ('name', models.CharField(max_length=255, verbose_name='InternationalSchool|name')),
                ('link', models.URLField(verbose_name='Online Course|Link')),
                ('place', models.CharField(max_length=255, verbose_name='InternationalSchool|place')),
                ('deadline', models.DateField(verbose_name='InternationalSchool|Deadline')),
                ('has_grants', models.BooleanField(default=False, verbose_name='InternationalSchool|Grants')),
            ],
            options={
                'ordering': ['name'],
                'db_table': 'international_schools',
                'verbose_name': 'International school',
                'verbose_name_plural': 'International schools',
            },
        ),
    ]
