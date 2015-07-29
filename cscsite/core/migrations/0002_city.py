# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='City',
            fields=[
                ('code', models.CharField(help_text='UN/LOCODE notification preferable', max_length=6, serialize=False, verbose_name='Code', primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='City name')),
                ('name_ru', models.CharField(max_length=255, null=True, verbose_name='City name')),
                ('name_en', models.CharField(max_length=255, null=True, verbose_name='City name')),
            ],
            options={
                'ordering': ['name'],
                'db_table': 'cities',
                'verbose_name': 'City',
                'verbose_name_plural': 'Cities',
            },
        ),
    ]
