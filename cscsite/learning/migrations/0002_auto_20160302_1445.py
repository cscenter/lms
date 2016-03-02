# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('learning', '0001_initial'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentproject',
            name='students',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL, verbose_name='Students'),
        ),
        migrations.AddField(
            model_name='studentassignment',
            name='assignment',
            field=models.ForeignKey(verbose_name='StudentAssignment|assignment', to='learning.Assignment'),
        ),
        migrations.AddField(
            model_name='studentassignment',
            name='student',
            field=models.ForeignKey(verbose_name='StudentAssignment|student', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='semester',
            unique_together=set([('year', 'type')]),
        ),
        migrations.AddField(
            model_name='noncourseevent',
            name='venue',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='CourseClass|Venue', to='learning.Venue'),
        ),
        migrations.AddField(
            model_name='enrollment',
            name='course_offering',
            field=models.ForeignKey(verbose_name='Course offering', to='learning.CourseOffering'),
        ),
        migrations.AddField(
            model_name='enrollment',
            name='student',
            field=models.ForeignKey(verbose_name='Student', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='courseofferingteacher',
            name='course_offering',
            field=models.ForeignKey(to='learning.CourseOffering'),
        ),
        migrations.AddField(
            model_name='courseofferingteacher',
            name='teacher',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='courseofferingnewsnotification',
            name='course_offering_news',
            field=models.ForeignKey(verbose_name='Course offering news', to='learning.CourseOfferingNews'),
        ),
        migrations.AddField(
            model_name='courseofferingnewsnotification',
            name='user',
            field=models.ForeignKey(verbose_name='User', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='courseofferingnews',
            name='author',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Author', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='courseofferingnews',
            name='course_offering',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Course offering', to='learning.CourseOffering'),
        ),
        migrations.AddField(
            model_name='courseoffering',
            name='city',
            field=models.ForeignKey(default=b'RU SPB', blank=True, to='core.City', null=True),
        ),
        migrations.AddField(
            model_name='courseoffering',
            name='course',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Course', to='learning.Course'),
        ),
        migrations.AddField(
            model_name='courseoffering',
            name='enrolled_students',
            field=models.ManyToManyField(related_name='enrolled_on_set', verbose_name='Enrolled students', to=settings.AUTH_USER_MODEL, through='learning.Enrollment', blank=True),
        ),
        migrations.AddField(
            model_name='courseoffering',
            name='semester',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Semester', to='learning.Semester'),
        ),
        migrations.AddField(
            model_name='courseoffering',
            name='teachers',
            field=models.ManyToManyField(related_name='teaching_set', verbose_name='Course|teachers', through='learning.CourseOfferingTeacher', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='courseclassattachment',
            name='course_class',
            field=models.ForeignKey(verbose_name='Class', to='learning.CourseClass'),
        ),
        migrations.AddField(
            model_name='courseclass',
            name='course_offering',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Course offering', to='learning.CourseOffering'),
        ),
        migrations.AddField(
            model_name='courseclass',
            name='venue',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='CourseClass|Venue', to='learning.Venue'),
        ),
        migrations.AddField(
            model_name='assignmentnotification',
            name='student_assignment',
            field=models.ForeignKey(verbose_name='student_assignment', to='learning.StudentAssignment'),
        ),
        migrations.AddField(
            model_name='assignmentnotification',
            name='user',
            field=models.ForeignKey(verbose_name='User', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='assignmentcomment',
            name='author',
            field=models.ForeignKey(verbose_name='Author', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='assignmentcomment',
            name='student_assignment',
            field=models.ForeignKey(verbose_name='AssignmentComment|student_assignment', to='learning.StudentAssignment'),
        ),
        migrations.AddField(
            model_name='assignmentattachment',
            name='assignment',
            field=models.ForeignKey(verbose_name='Assignment', to='learning.Assignment'),
        ),
        migrations.AddField(
            model_name='assignment',
            name='assigned_to',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL, verbose_name='Assignment|assigned_to', through='learning.StudentAssignment', blank=True),
        ),
        migrations.AddField(
            model_name='assignment',
            name='course_offering',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Course offering', to='learning.CourseOffering'),
        ),
        migrations.AlterUniqueTogether(
            name='studentassignment',
            unique_together=set([('assignment', 'student')]),
        ),
        migrations.AlterUniqueTogether(
            name='enrollment',
            unique_together=set([('student', 'course_offering')]),
        ),
    ]
