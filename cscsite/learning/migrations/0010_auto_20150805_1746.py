# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
        ('learning', '0009_venue_site'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='venue',
            name='site',
        ),
        migrations.AddField(
            model_name='venue',
            name='sites',
            field=models.ManyToManyField(to='sites.Site'),
        ),
    ]
