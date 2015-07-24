# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0003_onlinecourse'),
    ]

    operations = [
        migrations.AlterField(
            model_name='courseclass',
            name='video',
            field=models.TextField(help_text='\u0414\u043e\u0441\u0442\u0443\u043f\u043d\u044b LaTeX+<a href="http://ru.wikipedia.org/wiki/Markdown">Markdown</a>+HTML; \u043f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430, \u0432\u0441\u0442\u0430\u0432\u044c\u0442\u0435 HTML \u0434\u043b\u044f \u0432\u0441\u0442\u0440\u043e\u0435\u043d\u043d\u043e\u0433\u043e \u0432\u0438\u0434\u0435\u043e\u043f\u043b\u0435\u0435\u0440\u0430', verbose_name='CourseClass|Video', blank=True),
        ),
    ]
