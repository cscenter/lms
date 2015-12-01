# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from itertools import groupby
from django.db import migrations, models

def forwards(apps, schema_editor):
    StudentProjectClass = apps.get_model('learning', 'StudentProject')
    student_projects = StudentProjectClass.objects.order_by("name",
                                                            "semester_id").all()
    for name, group_by_name in groupby(student_projects,
                                       key=lambda x: (x.name, x.semester_id)):
        group = list(group_by_name)
        if len(group) == 1:
            continue
        project = group[0]
        students = [student.pk for p in group for student in
                    p.students.all()]
        project.students.add(*students)
        remove_projects = [p.pk for p in group[1:]]
        StudentProjectClass.objects.filter(pk__in=remove_projects).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0029_auto_20151126_1659'),
    ]

    operations = [
        migrations.RunPython(forwards),
    ]
