# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_auto_20150724_1656'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cscuser',
            name='uni_year_at_enrollment',
            field=models.CharField(choices=[(1, '1 course bachelor, speciality'), (2, '2 course bachelor, speciality'), (3, '3 course bachelor, speciality'), (4, '4 course bachelor, speciality'), (5, 'last course speciality'), (6, '1 course magistracy'), (7, '2 course magistracy'), (8, 'postgraduate'), (9, 'graduate')], max_length=2, blank=True, help_text='at enrollment', null=True, verbose_name='StudentInfo|University year'),
        ),
    ]
