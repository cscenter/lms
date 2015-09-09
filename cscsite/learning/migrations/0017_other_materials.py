# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from django.db import models, migrations


def forwards(apps, schema_editor):
    CourseClass = apps.get_model('learning', 'CourseClass')
    course_classes = CourseClass.objects.all()
    for course_class in course_classes:
        if not course_class.video_url:
            course_class.other_materials = course_class.video + course_class.other_materials


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0016_populate_video_url_yandex'),
    ]

    operations = [
        migrations.RunPython(forwards),
    ]
