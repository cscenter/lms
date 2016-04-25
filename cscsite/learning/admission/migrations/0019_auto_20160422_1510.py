# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0018_auto_20160419_1220'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='online_test_max_score',
            field=models.SmallIntegerField(default=0, verbose_name='Campaign|Test_max_score'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='campaign',
            name='online_test_passing_score',
            field=models.SmallIntegerField(default=0, verbose_name='Campaign|Test_passing_score'),
            preserve_default=False,
        ),
    ]
