# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0010_auto_20160331_1310'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentproject',
            name='grade',
            field=model_utils.fields.StatusField(default='not_graded', max_length=100, verbose_name='Grade', no_check_for_status=True, choices=[(0, 'dummy')]),
        ),
        migrations.AlterUniqueTogether(
            name='courseofferingteacher',
            unique_together=set([]),
        ),
    ]
