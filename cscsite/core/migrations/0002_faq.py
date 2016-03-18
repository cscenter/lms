# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Faq',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('question', models.CharField(max_length=255, verbose_name='Question')),
                ('answer', models.TextField(verbose_name='Answer')),
                ('sort', models.SmallIntegerField(verbose_name='Sort order')),
                ('sites', models.ManyToManyField(to='sites.Site')),
            ],
            options={
                'ordering': ['sort'],
                'db_table': 'faq',
                'verbose_name': 'FAQ',
                'verbose_name_plural': 'Questions&Answers',
            },
        ),
    ]
