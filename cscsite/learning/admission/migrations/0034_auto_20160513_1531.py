# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0033_auto_20160513_1518'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='interview',
            name='decision',
        ),
        migrations.RemoveField(
            model_name='interview',
            name='decision_comment',
        ),
        migrations.AddField(
            model_name='interview',
            name='note',
            field=models.TextField(null=True, verbose_name='Note', blank=True),
        ),
        migrations.AddField(
            model_name='interview',
            name='status',
            field=models.CharField(default='approval', max_length=15, verbose_name='Interview|Status', choices=[('approval', 'Approval'), ('deferred', 'Deferred'), ('canceled', 'Canceled'), ('waiting', 'Waiting for interview'), ('completed', 'Completed')]),
        ),
    ]
