# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0033_auto_20151230_1159'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='courseofferingteacher',
            options={'verbose_name': 'Course Offering teacher'},
        ),
    ]
