# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0006_auto_20160225_1420'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='internationalschool',
            name='end',
        ),
        migrations.RemoveField(
            model_name='internationalschool',
            name='start',
        ),
        migrations.AddField(
            model_name='internationalschool',
            name='ends_at',
            field=models.DateField(default=datetime.datetime(2016, 2, 25, 11, 23, 17, 453656, tzinfo=utc), verbose_name='InternationalSchool|End'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='internationalschool',
            name='starts_at',
            field=models.DateField(default=datetime.datetime(2016, 2, 25, 11, 23, 24, 669759, tzinfo=utc), verbose_name='InternationalSchool|Start'),
            preserve_default=False,
        ),
    ]
