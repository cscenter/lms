# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0020_co_is_completed_and_attachment_alter_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assignmentstudent',
            name='last_commented',
            field=models.DateTimeField(null=True, verbose_name='Last comment date', blank=True),
        ),
    ]
