# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def forwards_func(apps, schema_editor):
    """
    All existing students are "CSCenter students"
    """
    StudyProgram = apps.get_model('users', 'CSCUser')
    db_alias = schema_editor.connection.alias
    (StudyProgram.objects.using(db_alias)
     .filter(groups__pk=1)
     .update(is_center_student=True))


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_cscuser_study_programs'),
    ]

    operations = [
        migrations.RunPython(forwards_func),
    ]
