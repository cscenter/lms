# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0009_auto_20160328_1757'),
    ]

    operations = [
        migrations.AddField(
            model_name='interviewer',
            name='campaign',
            field=models.ForeignKey(related_name='interviewers', on_delete=django.db.models.deletion.PROTECT, default=1, verbose_name='Interviewer|Campaign', to='admission.Campaign'),
            preserve_default=False,
        ),
    ]
