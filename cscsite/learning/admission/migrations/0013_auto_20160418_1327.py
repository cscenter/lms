# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0012_auto_20160415_1832'),
    ]

    operations = [
        migrations.AlterField(
            model_name='test',
            name='applicant',
            field=models.OneToOneField(related_name='online_test', on_delete=django.db.models.deletion.PROTECT, verbose_name='Applicant', to='admission.Applicant'),
        ),
    ]
