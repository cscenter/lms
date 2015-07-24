# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_auto_20150721_1403'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cscuser',
            name='private_contacts',
            field=models.TextField(help_text='\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b LaTeX \u0438 Markdown; \u043f\u043e\u043a\u0430\u0437\u044b\u0432\u0430\u0435\u0442\u0441\u044f \u0442\u043e\u043b\u044c\u043a\u043e \u0437\u0430\u043b\u043e\u0433\u0438\u043d\u0435\u043d\u043d\u044b\u043c \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f\u043c', verbose_name='Contact information', blank=True),
        ),
    ]
