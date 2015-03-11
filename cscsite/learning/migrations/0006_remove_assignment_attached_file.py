# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0005_assignmentattachment'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='assignment',
            name='attached_file',
        ),
    ]
