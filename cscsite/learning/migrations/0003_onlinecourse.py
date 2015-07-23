# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import sorl.thumbnail.fields
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0002_auto_20150615_1637'),
    ]

    operations = [
        migrations.CreateModel(
            name='OnlineCourse',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('start', models.DateTimeField(null=True, verbose_name='start', blank=True)),
                ('end', models.DateTimeField(null=True, verbose_name='end', blank=True)),
                ('name', models.CharField(max_length=255, verbose_name='Course|name')),
                ('teachers', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', verbose_name='Online Course|teachers')),
                ('description', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', verbose_name='Online Course|description')),
                ('link', models.URLField(verbose_name='Online Course|Link')),
                ('photo', sorl.thumbnail.fields.ImageField(upload_to='online_courses/', verbose_name='Online Course|photo', blank=True)),
            ],
            options={
                'ordering': ['name'],
                'db_table': 'online_courses',
                'verbose_name': 'Online course',
                'verbose_name_plural': 'Online courses',
            },
        ),
    ]
