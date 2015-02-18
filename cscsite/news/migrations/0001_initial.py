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
            name='News',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('title', models.CharField(max_length=140, verbose_name='News|title')),
                ('published', models.BooleanField(default=True, verbose_name='News|published')),
                ('slug', models.SlugField(help_text='Short dash-separated string for human-readable URLs, as in test.com/news/<b>some-news</b>/', unique=True, max_length=70, verbose_name='News|slug')),
                ('text', model_utils.fields.SplitField(help_text='\u041f\u0435\u0440\u0432\u044b\u0435 2 \u043f\u0430\u0440\u0430\u0433\u0440\u0430\u0444\u043e\u0432 \u0438\u043b\u0438 \u0432\u0441\u0451 \u0434\u043e &lt;!-- split --&gt; \u0431\u0443\u0434\u0443\u0442 \u0432\u044b\u0434\u0435\u0440\u0436\u043a\u043e\u0439; \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b LaTeX \u0438 Markdown', verbose_name='News|text')),
                ('_text_excerpt', models.TextField(editable=False)),
            ],
            options={
                'ordering': ['-created', 'author'],
                'verbose_name': 'News|news-singular',
                'verbose_name_plural': 'News|news-plural',
            },
            bases=(models.Model,),
        ),
    ]
