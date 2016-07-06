# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0040_auto_20160706_1135'),
    ]

    operations = [
        migrations.AlterField(
            model_name='interview',
            name='applicant',
            field=models.ForeignKey(related_name='interviews', on_delete=django.db.models.deletion.PROTECT, verbose_name='Applicant', to='admission.Applicant'),
        ),
    ]
