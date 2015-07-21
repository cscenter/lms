# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_auto_20150721_1359'),
    ]

    operations = [
        migrations.AlterField(
            model_name='shadcourserecord',
            name='grade',
            field=model_utils.fields.StatusField(default='not_graded', max_length=100, verbose_name='Enrollment|grade', no_check_for_status=True, choices=[(0, 'dummy')]),
        ),
    ]
