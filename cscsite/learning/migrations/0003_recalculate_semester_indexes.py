# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def recalculate_semester_indexes(apps, schema_editor):
    from django.core.management import call_command
    call_command('recalculate_semester_indexes')

class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0002_auto_20160302_1445'),
        ('learning', '0020_auto_20160718_1654'),
    ]

    operations = [
        migrations.RunPython(recalculate_semester_indexes),
    ]
