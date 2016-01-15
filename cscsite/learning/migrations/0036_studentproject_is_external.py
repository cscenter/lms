# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0035_auto_20151230_1213'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentproject',
            name='is_external',
            field=models.BooleanField(default=False, verbose_name='External project'),
        ),
    ]
