# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0009_auto_20160329_1805'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='courseofferingteacher',
            unique_together=set([('teacher', 'course_offering')]),
        ),
    ]
