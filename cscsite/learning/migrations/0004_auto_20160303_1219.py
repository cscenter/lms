# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0003_recalculate_semester_indexes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='internationalschool',
            name='ends_at',
            field=models.DateField(null=True, verbose_name='InternationalSchool|End', blank=True),
        ),
    ]
