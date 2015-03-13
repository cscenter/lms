# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def forwards_func(apps, schema_editor):
    StudyProgram = apps.get_model('learning', 'StudyProgram')
    db_alias = schema_editor.connection.alias
    StudyProgram.objects.using(db_alias).bulk_create([
        StudyProgram(code="dm", name="Data mining"),
        StudyProgram(code="cs", name="Computer Science"),
        StudyProgram(code="se", name="Software Engineering"),
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0007_auto_20150313_1800'),
    ]

    operations = [
        migrations.RunPython(forwards_func),
    ]
