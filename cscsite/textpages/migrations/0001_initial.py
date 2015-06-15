# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import model_utils.fields


def forwards_func(apps, schema_editor):
    Textpage = apps.get_model('textpages', 'Textpage')
    db_alias = schema_editor.connection.alias
    initial_pages = [{
                        "url_name": "syllabus",
                        "name": "Syllabus",
                        "text": "# Syllabus\n\nThis is Computer Science Center syllabus. **Please change this text**."},
                     {
                        "url_name": "orgs",
                        "name": "Organizers",
                        "text": "# Organizers\n\nThis is a list of people that made Computer Science Center real. **Please change this text**."},
                     {
                        "url_name": "contacts",
                        "name": "Contacts",
                        "text": "# Contacts\r\n\r\nThis is how you can contact Computer Science Center. **Please change this text**.\r\n\r\n[CSCenter learning venues](/venues)"},
                     {
                        "url_name": "enrollment",
                        "name": "Enrollment",
                        "text": "# Enrollment\n\nThis is how you can enroll at Computer Science Center. **Please change this text**."},
                     {
                        "url_name": "useful_stuff",
                        "name": "Useful stuff",
                        "text": "# Licenses\n\nThis is a list of licenses available for Computer Science Center students. **Please change this text**."},
                     {
                        "url_name": "online",
                        "name": "Online",
                        "text": "# Online\n\nThis is \"online\" page. **Please change this text**."},
                     {
                        "url_name": "lectures",
                        "name": "Lectures",
                        "text": "# Lectures\n\nThis is \"lectures\" page. **Please change this text**."}]
    for page in initial_pages:
        Textpage(**page).save(force_insert=True, using=db_alias)

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
        ),
        migrations.RunPython(forwards_func),
    ]
