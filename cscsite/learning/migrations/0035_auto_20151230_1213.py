# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0034_auto_20151230_1209'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='courseofferingteacher',
            options={'verbose_name': 'Course Offering teacher', 'verbose_name_plural': 'Course Offering teachers'},
        ),
    ]
