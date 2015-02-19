# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def forwards_func(apps, schema_editor):
    StudyProgram = apps.get_model('learning', 'StudyProgram')
    db_alias = schema_editor.connection.alias
    StudyProgram.objects.using(db_alias).bulk_create([
        StudyProgram(name="Data mining"),
        StudyProgram(name="Computer Science"),
        StudyProgram(name="Software Engineering"),
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0003_studyprograms'),
    ]

    operations = [
        migrations.RunPython(forwards_func),
    ]
