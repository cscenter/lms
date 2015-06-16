# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def forwards_func(apps, schema_editor):
    # Add sites
    Site = apps.get_model('sites', 'Site')
    db_alias = schema_editor.connection.alias
    Site(name="compscicenter.ru", domain='compscicenter.ru').save(force_insert=True, using=db_alias)
    Site(name="compsciclub.ru", domain='compsciclub.ru').save(force_insert=True, using=db_alias)


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(forwards_func),
    ]
