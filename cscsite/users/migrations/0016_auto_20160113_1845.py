# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0015_remove_cscuser_status_changed_at'),
    ]

    operations = [
        migrations.RenameField(
            model_name='cscuser',
            old_name='status_changed_at2',
            new_name='status_changed_at',
        ),
    ]
