# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_cscuserreference'),
    ]

    operations = [
        migrations.AddField(
            model_name='cscuser',
            name='gender',
            field=models.CharField(default='M', max_length=1, choices=[('M', 'Male'), ('F', 'Female')]),
            preserve_default=False,
        ),
    ]
