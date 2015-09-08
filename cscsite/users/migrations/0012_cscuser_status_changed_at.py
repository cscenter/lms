# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_cscuser_modified'),
    ]

    operations = [
        migrations.AddField(
            model_name='cscuser',
            name='status_changed_at',
            field=model_utils.fields.MonitorField(default=django.utils.timezone.now, verbose_name='Status changed', monitor='status'),
        ),
    ]
