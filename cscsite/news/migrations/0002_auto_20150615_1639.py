# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='news',
            name='text',
            field=model_utils.fields.SplitField(help_text='First 2 paragraphs or anything before &lt;!-- split --&gt; will serve as excerpt; LaTeX+Markdown is enabled', no_excerpt_field=True, verbose_name='News|text'),
        ),
    ]
