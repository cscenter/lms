# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0030_auto_20160429_1310'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='interviewer',
            field=models.ForeignKey(related_name='interview_comments', on_delete=django.db.models.deletion.PROTECT, verbose_name='Interviewer', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='test',
            name='score',
            field=models.PositiveSmallIntegerField(verbose_name='Score'),
        ),
    ]
