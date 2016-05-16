# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0034_auto_20160513_1531'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='current',
            field=models.BooleanField(default=False, verbose_name='Current campaign'),
        ),
    ]
