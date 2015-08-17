# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_update_uni_year_at_enrollment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cscuser',
            name='university',
            field=models.CharField(max_length=255, verbose_name='University', blank=True),
        ),
    ]
