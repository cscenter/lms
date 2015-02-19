# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_auto_20150219_2025'),
    ]

    operations = [
        migrations.RenameField(
            model_name='cscuser',
            old_name='comment_changed',
            new_name='comment_changed_at',
        ),
    ]
