# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0013_auto_20160418_1327'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exam',
            name='applicant',
            field=models.ForeignKey(related_name='exam', on_delete=django.db.models.deletion.PROTECT, verbose_name='Applicant', to='admission.Applicant'),
        ),
    ]
