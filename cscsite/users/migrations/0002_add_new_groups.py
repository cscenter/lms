# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from users.models import CSCUser


def forwards_func(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    db_alias = schema_editor.connection.alias
    Group(name="Volunteer").save(force_insert=True, using=db_alias)
    Group(name="Student [CLUB]").save(force_insert=True, using=db_alias)
    Group(name="Teacher [CLUB]").save(force_insert=True, using=db_alias)
    # Rename existing groups
    g = Group.objects.get(pk=CSCUser.group_pks.STUDENT_CENTER)
    g.name = "Student [CENTER]"
    g.save(using=db_alias)

    g = Group.objects.get(pk=CSCUser.group_pks.TEACHER_CENTER)
    g.name = "Teacher [CENTER]"
    g.save(using=db_alias)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(forwards_func)
    ]
