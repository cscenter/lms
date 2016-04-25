# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0020_auto_20160422_1524'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='score',
            field=models.SmallIntegerField(verbose_name='Score', validators=[django.core.validators.MinValueValidator(-2), django.core.validators.MaxValueValidator(2)]),
        ),
    ]
