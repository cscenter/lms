# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0004_auto_20160322_1523'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicant',
            name='uuid',
            field=models.UUIDField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='exam',
            name='uuid',
            field=models.UUIDField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='test',
            name='uuid',
            field=models.UUIDField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='test',
            name='applicant',
            field=models.ForeignKey(related_name='online_tests', on_delete=django.db.models.deletion.PROTECT, verbose_name='Applicant', to='admission.Applicant'),
        ),
    ]
