# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def forwards(apps, schema_editor):
    StudentProjectClass = apps.get_model('learning', 'StudentProject')
    student_projects = StudentProjectClass.objects.all()
    for project in student_projects:
        project.students.add(project.student.pk)

class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0027_studentproject_students'),
        ('users', '0004_remove_cscuser_is_center_student'),
    ]

    operations = [
        migrations.RunPython(forwards),
    ]
