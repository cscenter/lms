# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CustomTextpage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('slug', models.SlugField(help_text='Short dash-separated string for human-readable URLs, as in compscicenter.ru/pages/<b>some-news</b>/', unique=True, max_length=70, verbose_name='News|slug')),
                ('name', models.CharField(max_length=100, verbose_name='Textpage|name')),
                ('text', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', verbose_name='News|text')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Textpage|Custom page',
                'verbose_name_plural': 'Textpage|Custom pages',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Textpage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('url_name', models.CharField(verbose_name='Textpage|url_name', unique=True, max_length=100, editable=False)),
                ('name', models.CharField(verbose_name='Textpage|name', max_length=100, editable=False)),
                ('text', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', verbose_name='News|text')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Textpage|page',
                'verbose_name_plural': 'Textpage|pages',
            },
            bases=(models.Model,),
        ),
    ]
