# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0003_auto_20150729_1609'),
    ]

    operations = [
        migrations.AlterField(
            model_name='news',
            name='cities',
            field=models.ManyToManyField(to='core.City', null=True, blank=True),
        ),
    ]
