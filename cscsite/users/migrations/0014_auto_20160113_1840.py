# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import users.models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0035_auto_20151230_1213'),
        ('users', '0013_auto_20160113_1521'),
    ]

    operations = [
        migrations.AddField(
            model_name='cscuser',
            name='status_changed_at2',
            field=users.models.MonitorFKField(monitor='status', log_class=users.models.CSCUserStatusLog, blank=True, to='learning.Semester', help_text='Automatically updated when status changed, but you still can set it manually', null=True, verbose_name='Status changed'),
        ),
        migrations.AlterField(
            model_name='cscuser',
            name='status_changed_at',
            field=users.models.MonitorDateField(monitor='status', log_class=users.models.CSCUserStatusLog, blank=True, help_text='Automatically updated when status changed, but you still can set it manually', null=True, verbose_name='Status changed'),
        ),
    ]
