# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
        ('core', '0003_auto_20150729_1623'),
        ('news', '0006_auto_20150729_1805'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='news',
            name='cities',
        ),
        migrations.RemoveField(
            model_name='news',
            name='sites',
        ),
        migrations.AddField(
            model_name='news',
            name='city',
            field=models.ForeignKey(to='core.City', null=True),
        ),
        migrations.AddField(
            model_name='news',
            name='site',
            field=models.ForeignKey(default=1, to='sites.Site'),
            preserve_default=False,
        ),
    ]
