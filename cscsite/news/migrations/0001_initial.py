# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='News',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('title', models.CharField(max_length=140, verbose_name='News|title')),
                ('published', models.BooleanField(default=True, verbose_name='News|published')),
                ('slug', models.SlugField(help_text='Short dash-separated string for human-readable URLs, as in test.com/news/<b>some-news</b>/', unique=True, max_length=70, verbose_name='News|slug')),
                ('text', model_utils.fields.SplitField(help_text='First 2 paragraphs or anything before &lt;!-- split --&gt; will serve as excerpt; LaTeX+Markdown is enabled', no_excerpt_field=False, verbose_name='News|text')),
                ('_text_excerpt', models.TextField(editable=False)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, editable=False, to=settings.AUTH_USER_MODEL, null=True, verbose_name='News|author')),
            ],
            options={
                'ordering': ['-created', 'author'],
                'verbose_name': 'News|news-singular',
                'verbose_name_plural': 'News|news-plural',
            },
        ),
    ]
