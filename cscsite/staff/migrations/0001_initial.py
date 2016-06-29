# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Hint',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('question', models.CharField(max_length=255, verbose_name='Question')),
                ('answer', models.TextField(verbose_name='Answer')),
                ('sort', models.SmallIntegerField(null=True, verbose_name='Sort order', blank=True)),
            ],
            options={
                'ordering': ['sort'],
                'verbose_name': 'Warehouse',
                'verbose_name_plural': 'Warehouses',
            },
        ),
    ]
