# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='cscuser',
            name='photo_data',
            field=jsonfield.fields.JSONField(null=True, blank=True),
        ),
    ]
