# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0005_news_language'),
    ]

    operations = [
        migrations.AlterField(
            model_name='news',
            name='cities',
            field=models.ManyToManyField(to='core.City', blank=True),
        ),
    ]
