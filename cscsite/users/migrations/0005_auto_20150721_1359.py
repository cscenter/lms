# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0002_auto_20150615_1637'),
        ('users', '0004_remove_cscuser_is_center_student'),
    ]

    operations = [
        migrations.AddField(
            model_name='shadcourserecord',
            name='semester',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, default=1, verbose_name='Semester', to='learning.Semester'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='shadcourserecord',
            name='teachers',
            field=models.CharField(default='', max_length=255, verbose_name='Teachers'),
            preserve_default=False,
        ),
    ]
