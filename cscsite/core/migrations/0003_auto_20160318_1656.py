# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_faq'),
    ]

    operations = [
        migrations.AlterField(
            model_name='faq',
            name='sites',
            field=models.ManyToManyField(to='sites.Site', verbose_name='Sites'),
        ),
        migrations.AlterField(
            model_name='faq',
            name='sort',
            field=models.SmallIntegerField(null=True, verbose_name='Sort order', blank=True),
        ),
    ]
