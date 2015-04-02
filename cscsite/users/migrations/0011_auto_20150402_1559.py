# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_auto_20150313_1824'),
    ]

    operations = [
        migrations.AddField(
            model_name='cscuser',
            name='github_id',
            field=models.CharField(blank=True, max_length=80, verbose_name='Github ID', validators=[django.core.validators.RegexValidator(regex='^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]$')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='cscuser',
            name='is_center_student',
            field=models.BooleanField(default=False, help_text="Students without this flag belong to CSClub only and can't enroll to CSCenter's courses", verbose_name='Student of CSCenter'),
            preserve_default=True,
        ),
    ]
