# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
        ('learning', '0004_auto_20160303_1219'),
    ]

    operations = [
        migrations.CreateModel(
            name='Useful',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('question', models.CharField(max_length=255, verbose_name='Question')),
                ('answer', models.TextField(verbose_name='Answer')),
                ('sort', models.SmallIntegerField(null=True, verbose_name='Sort order', blank=True)),
                ('site', models.ForeignKey(default=1, verbose_name='Site', to='sites.Site')),
            ],
            options={
                'ordering': ['sort'],
                'verbose_name': 'Useful',
                'verbose_name_plural': 'Useful',
            },
        ),
    ]
