# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0024_auto_20160425_1612'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exam',
            name='score',
            field=models.PositiveSmallIntegerField(verbose_name='Score'),
        ),
    ]
