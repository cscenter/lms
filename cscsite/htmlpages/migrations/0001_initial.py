# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HtmlPage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.CharField(max_length=100, verbose_name='URL', db_index=True)),
                ('title', models.CharField(max_length=200, verbose_name='title')),
                ('title_ru', models.CharField(max_length=200, null=True, verbose_name='title')),
                ('title_en', models.CharField(max_length=200, null=True, verbose_name='title')),
                ('content', models.TextField(verbose_name='content', blank=True)),
                ('content_ru', models.TextField(null=True, verbose_name='content', blank=True)),
                ('content_en', models.TextField(null=True, verbose_name='content', blank=True)),
                ('template_name', models.CharField(help_text="Example: 'htmlpages/contact_page.html'. If this isn't provided, the system will use 'htmlpages/default.html'.", max_length=70, verbose_name='template name', blank=True)),
                ('registration_required', models.BooleanField(default=False, help_text='If this is checked, only logged-in users will be able to view the page.', verbose_name='registration required')),
                ('sites', models.ManyToManyField(to='sites.Site')),
            ],
            options={
                'ordering': ('url',),
                'db_table': 'htmlpages',
                'verbose_name': 'flat page',
                'verbose_name_plural': 'flat pages',
            },
        ),
    ]
