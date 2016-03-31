# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0007_assignment_notify_settings'),
    ]

    operations = [
        migrations.RenameField(
            model_name='assignment',
            old_name='notify_settings',
            new_name='notify_teachers',
        ),
    ]
