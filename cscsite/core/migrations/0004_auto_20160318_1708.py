# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
        ('core', '0003_auto_20160318_1656'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='faq',
            name='sites',
        ),
        migrations.AddField(
            model_name='faq',
            name='site',
            field=models.ForeignKey(default=1, verbose_name='Site', to='sites.Site'),
        ),
    ]
