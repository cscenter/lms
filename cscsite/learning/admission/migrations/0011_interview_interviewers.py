# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0010_interviewer_campaign'),
    ]

    operations = [
        migrations.AddField(
            model_name='interview',
            name='interviewers',
            field=models.ManyToManyField(to='admission.Interviewer', verbose_name='Interview|Interviewers'),
        ),
    ]
