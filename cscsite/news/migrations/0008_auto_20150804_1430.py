# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0007_auto_20150804_1246'),
    ]

    operations = [
        migrations.AlterField(
            model_name='news',
            name='city',
            field=models.ForeignKey(blank=True, to='core.City', null=True),
        ),
    ]
