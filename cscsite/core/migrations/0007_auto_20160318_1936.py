# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_auto_20160318_1920'),
    ]

    operations = [
        migrations.AlterField(
            model_name='faq',
            name='categories',
            field=models.ManyToManyField(related_name='categories', verbose_name='Categories', to='core.FaqCategory', blank=True),
        ),
    ]
