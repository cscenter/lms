# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def forwards_func(apps, schema_editor):
    City = apps.get_model('learning', 'City')
    db_alias = schema_editor.connection.alias
    City.objects.using(db_alias).bulk_create([
        City(code="RU LED", name="Saint Petersburg"),
        City(code="RU KZN", name="Kazan"),
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0010_auto_20150313_1812'),
    ]

    operations = [
        migrations.RunPython(forwards_func),
    ]
