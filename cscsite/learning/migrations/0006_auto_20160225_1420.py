# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0005_internationalschool'),
    ]

    operations = [
        migrations.AlterField(
            model_name='internationalschool',
            name='link',
            field=models.URLField(verbose_name='InternationalSchool|Link'),
        ),
    ]
