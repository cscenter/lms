# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('learning', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentproject',
            name='student',
            field=models.ForeignKey(verbose_name='AssignmentStudent|student', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='noncourseevent',
            name='venue',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='CourseClass|Venue', to='learning.Venue'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='enrollment',
            name='course_offering',
            field=models.ForeignKey(verbose_name='Course offering', to='learning.CourseOffering'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='enrollment',
            name='student',
            field=models.ForeignKey(verbose_name='Student', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='enrollment',
            unique_together=set([('student', 'course_offering')]),
        ),
        migrations.AddField(
            model_name='courseofferingnewsnotification',
            name='course_offering_news',
            field=models.ForeignKey(verbose_name='Course offering news', to='learning.CourseOfferingNews'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseofferingnewsnotification',
            name='user',
            field=models.ForeignKey(verbose_name='User', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseofferingnews',
            name='author',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Author', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseofferingnews',
            name='course_offering',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Course offering', to='learning.CourseOffering'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseoffering',
            name='course',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Course', to='learning.Course'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseoffering',
            name='enrolled_students',
            field=models.ManyToManyField(related_name='enrolled_on_set', verbose_name='Enrolled students', to=settings.AUTH_USER_MODEL, through='learning.Enrollment', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseoffering',
            name='semester',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Semester', to='learning.Semester'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseoffering',
            name='teachers',
            field=models.ManyToManyField(related_name='teaching_set', verbose_name='Course|teachers', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseclassattachment',
            name='course_class',
            field=models.ForeignKey(verbose_name='Class', to='learning.CourseClass'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseclass',
            name='course_offering',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Course offering', to='learning.CourseOffering'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='courseclass',
            name='venue',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='CourseClass|Venue', to='learning.Venue'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='assignmentstudent',
            name='assignment',
            field=models.ForeignKey(verbose_name='AssignmentStudent|assignment', to='learning.Assignment'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='assignmentstudent',
            name='student',
            field=models.ForeignKey(verbose_name='AssignmentStudent|student', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='assignmentstudent',
            unique_together=set([('assignment', 'student')]),
        ),
        migrations.AddField(
            model_name='assignmentnotification',
            name='assignment_student',
            field=models.ForeignKey(verbose_name='assignment_student', to='learning.AssignmentStudent'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='assignmentnotification',
            name='user',
            field=models.ForeignKey(verbose_name='User', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='assignmentcomment',
            name='assignment_student',
            field=models.ForeignKey(verbose_name='AssignmentComment|assignment_student', to='learning.AssignmentStudent'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='assignmentcomment',
            name='author',
            field=models.ForeignKey(verbose_name='Author', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='assignment',
            name='assigned_to',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL, verbose_name='Assignment|assigned_to', through='learning.AssignmentStudent', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='assignment',
            name='course_offering',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Course offering', to='learning.CourseOffering'),
            preserve_default=True,
        ),
    ]
