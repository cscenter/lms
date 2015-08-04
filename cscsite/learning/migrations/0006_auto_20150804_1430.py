# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0005_delete_city'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='description_en',
            field=models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', null=True, verbose_name='Course|description'),
        ),
        migrations.AddField(
            model_name='course',
            name='description_ru',
            field=models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', null=True, verbose_name='Course|description'),
        ),
        migrations.AddField(
            model_name='course',
            name='name_en',
            field=models.CharField(max_length=140, null=True, verbose_name='Course|name'),
        ),
        migrations.AddField(
            model_name='course',
            name='name_ru',
            field=models.CharField(max_length=140, null=True, verbose_name='Course|name'),
        ),
        migrations.AddField(
            model_name='courseoffering',
            name='description_en',
            field=models.TextField(help_text='LaTeX+Markdown+HTML is enabled; empty description will be replaced by course description', null=True, verbose_name='Description', blank=True),
        ),
        migrations.AddField(
            model_name='courseoffering',
            name='description_ru',
            field=models.TextField(help_text='LaTeX+Markdown+HTML is enabled; empty description will be replaced by course description', null=True, verbose_name='Description', blank=True),
        ),
    ]
