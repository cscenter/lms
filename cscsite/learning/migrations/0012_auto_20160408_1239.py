# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0011_auto_20160408_1235'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='courseofferingteacher',
            unique_together=set([('teacher', 'course_offering')]),
        ),
    ]
