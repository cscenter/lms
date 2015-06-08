# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0010_courseoffering_is_open'),
    ]

    operations = [
        migrations.AlterField(
            model_name='courseclass',
            name='video',
            field=models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled; please insert HTML for embedded video player', verbose_name='CourseClass|Video', blank=True),
        ),
    ]
