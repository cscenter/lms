# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-02-13 10:41
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations
import core.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0017_auto_20180213_0852'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentassignment',
            name='grade',
            field=core.db.models.GradeField(blank=True, null=True, verbose_name='Grade'),
        ),
    ]
