# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0006_auto_20160323_1825'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='exam',
            name='uuid',
        ),
        migrations.RemoveField(
            model_name='test',
            name='uuid',
        ),
        migrations.AlterField(
            model_name='test',
            name='applicant',
            field=models.OneToOneField(related_name='online_tests', on_delete=django.db.models.deletion.PROTECT, verbose_name='Applicant', to='admission.Applicant'),
        ),
    ]
