# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gallery', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='album',
            name='semester',
            field=models.ForeignKey(verbose_name='Semester', blank=True, to='learning.Semester', null=True),
        ),
    ]
