# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_city'),
        ('sites', '0001_initial'),
        ('news', '0002_auto_20150724_1656'),
    ]

    operations = [
        migrations.AddField(
            model_name='news',
            name='cities',
            field=models.ManyToManyField(to='core.City'),
        ),
        migrations.AddField(
            model_name='news',
            name='sites',
            field=models.ManyToManyField(to='sites.Site'),
        ),
    ]
