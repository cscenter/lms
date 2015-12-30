# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import bitfield.models
from django.conf import settings

def forwards(apps, schema_editor):
    CourseOfferingClass = apps.get_model('learning', 'CourseOffering')
    UserClass = apps.get_model('users', 'CSCUser')
    course_offerings = CourseOfferingClass.objects.all()
    CourseOfferingTeacherClass = apps.get_model('learning', 'CourseOfferingTeacher')
    for co in course_offerings:
        for teacher in  co.teachers.all():
            m1 = CourseOfferingTeacherClass(teacher=teacher, course_offering=co)
            m1.save()

class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('learning', '0030_squash_student_projects'),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseOfferingTeacher',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('roles', bitfield.models.BitField((('lecturer', 'Lecturer'), ('reviewer', 'Reviewer')), default=1)),
                ('course_offering', models.ForeignKey(to='learning.CourseOffering')),
                ('teacher', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='courseoffering',
            name='teachers2',
            field=models.ManyToManyField(related_name='teaching_set2', verbose_name='Course|teachers', through='learning.CourseOfferingTeacher', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(forwards),
    ]
