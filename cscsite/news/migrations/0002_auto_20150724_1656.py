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
            field=model_utils.fields.SplitField(help_text='\u041f\u0435\u0440\u0432\u044b\u0435 2 \u043f\u0430\u0440\u0430\u0433\u0440\u0430\u0444\u043e\u0432 \u0438\u043b\u0438 \u0432\u0441\u0451 \u0434\u043e &lt;!-- split --&gt; \u0431\u0443\u0434\u0443\u0442 \u0432\u044b\u0434\u0435\u0440\u0436\u043a\u043e\u0439; \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b LaTeX \u0438 Markdown', no_excerpt_field=True, verbose_name='News|text'),
        ),
    ]
