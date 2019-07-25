# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('menu_extension', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='menuitemextension',
            name='open_in_new_window',
            field=models.BooleanField(default=False, help_text='Open link in new tab is selected'),
        ),
    ]
