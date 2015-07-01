# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_add_new_groups'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cscuser',
            name='nondegree',
        ),
        migrations.AlterField(
            model_name='cscuser',
            name='status',
            field=models.CharField(blank=True, max_length=15, verbose_name='Status', choices=[('expelled', 'StudentInfo|Expelled'), ('reinstated', 'StudentInfo|Reinstalled'), ('will_graduate', 'StudentInfo|Will graduate')]),
        ),
    ]
