# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0027_auto_20160428_1918'),
    ]

    operations = [
        migrations.AlterField(
            model_name='interview',
            name='assignments',
            field=models.ManyToManyField(to='admission.InterviewAssignment', verbose_name='Interview|Assignments', blank=True),
        ),
    ]
