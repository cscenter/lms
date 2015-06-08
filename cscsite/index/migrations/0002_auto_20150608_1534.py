# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='enrollmentapplemail',
            name='email',
            field=models.EmailField(max_length=254, verbose_name='email'),
        ),
    ]
