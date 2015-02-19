# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0002_auto_20150218_1956'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudyProgram',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('name', models.CharField(max_length=255, verbose_name='StudyProgram|Name')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Study program',
                'verbose_name_plural': 'Study programs',
            },
            bases=(models.Model,),
        ),
    ]
