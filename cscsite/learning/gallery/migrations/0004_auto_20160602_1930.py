# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gallery', '0003_auto_20160601_1616'),
    ]

    operations = [
        migrations.AlterField(
            model_name='image',
            name='semester',
            field=models.ForeignKey(verbose_name='Semester', blank=True, to='learning.Semester', null=True),
        ),
    ]
