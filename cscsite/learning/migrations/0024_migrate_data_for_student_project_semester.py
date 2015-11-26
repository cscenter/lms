# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def forwards(apps, schema_editor):
    """ Supports links from api 2.x. For 1.x fix manually """
    count = 0
    StudentProjectClass = apps.get_model('learning', 'StudentProject')
    student_projects = StudentProjectClass.objects.all()
    for project in student_projects:
        count = 0
        for semester in project.semesters.all():
            count += 1
            if count > 1:
                print("More then one semester for project {}".format(project.pk))
            project.semester_id = semester.pk
            project.save()

class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0023_studentproject_semester'),
    ]

    operations = [
        migrations.RunPython(forwards),
    ]
