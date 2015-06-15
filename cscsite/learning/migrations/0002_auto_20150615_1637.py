# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


def forwards_func(apps, schema_editor):
    # Add cities
    City = apps.get_model('learning', 'City')
    db_alias = schema_editor.connection.alias
    City.objects.using(db_alias).bulk_create([
        City(code="RU LED", name="Saint Petersburg"),
        City(code="RU KZN", name="Kazan"),
    ])
    # Add venues
    Venue = apps.get_model('learning', 'Venue')
    db_alias = schema_editor.connection.alias
    initial_venues = [{"name": "\u041f\u041e\u041c\u0418 \u0420\u0410\u041d",
                       "description": "\u041d\u0430\u0431\u0435\u0440\u0435\u0436\u043d\u0430\u044f \u0440\u0435\u043a\u0438 \u0424\u043e\u043d\u0442\u0430\u043d\u043a\u0438, 27, \u041c\u0440\u0430\u043c\u043e\u0440\u043d\u044b\u0439 \u0437\u0430\u043b (2 \u044d\u0442\u0430\u0436)\r\n\r\n<img src=\"//api-maps.yandex.ru/services/constructor/1.0/static/?sid=hlqT2p1Lqk9imQqe8w2gxQktaxSuP91c&width=600&height=450\" alt=\"\"/>"},
                      {"name": "\u0424\u041c\u041b 239",
                       "description": "\u0424\u0443\u0440\u0448\u0442\u0430\u0442\u0441\u043a\u0430\u044f \u0443\u043b\u0438\u0446\u0430, 9, \u0432\u0442\u043e\u0440\u043e\u0439 \u044d\u0442\u0430\u0436, \u0430\u043a\u0442\u043e\u0432\u044b\u0439 \u0437\u0430\u043b \u043b\u0438\u0431\u043e \u0430\u0443\u0434. 25 (\u0432 \u043a\u043e\u043d\u0446\u0435 \u043a\u043e\u0440\u0438\u0434\u043e\u0440\u0430)\r\n\r\n<img src=\"//api-maps.yandex.ru/services/constructor/1.0/static/?sid=95w30endKrJjcgE7ct5DTGxUgfGuvBgx&width=600&height=450\" alt=\"\"/>"}]
    for page in initial_venues:
        Venue(**page).save(force_insert=True, using=db_alias)
    # Add study programs
    StudyProgram = apps.get_model('learning', 'StudyProgram')
    db_alias = schema_editor.connection.alias
    StudyProgram.objects.using(db_alias).bulk_create([
        StudyProgram(code="dm", name="Data mining"),
        StudyProgram(code="cs", name="Computer Science"),
        StudyProgram(code="se", name="Software Engineering"),
    ])



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
            field=models.ManyToManyField(related_name='teaching_set', verbose_name='Course|teachers', to=settings.AUTH_USER_MODEL),
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
            model_name='assignmentstudent',
            name='assignment',
            field=models.ForeignKey(verbose_name='AssignmentStudent|assignment', to='learning.Assignment'),
        ),
        migrations.AddField(
            model_name='assignmentstudent',
            name='student',
            field=models.ForeignKey(verbose_name='AssignmentStudent|student', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='assignmentnotification',
            name='assignment_student',
            field=models.ForeignKey(verbose_name='assignment_student', to='learning.AssignmentStudent'),
        ),
        migrations.AddField(
            model_name='assignmentnotification',
            name='user',
            field=models.ForeignKey(verbose_name='User', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='assignmentcomment',
            name='assignment_student',
            field=models.ForeignKey(verbose_name='AssignmentComment|assignment_student', to='learning.AssignmentStudent'),
        ),
        migrations.AddField(
            model_name='assignmentcomment',
            name='author',
            field=models.ForeignKey(verbose_name='Author', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='assignmentattachment',
            name='assignment',
            field=models.ForeignKey(verbose_name='Assignment', to='learning.Assignment'),
        ),
        migrations.AddField(
            model_name='assignment',
            name='assigned_to',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL, verbose_name='Assignment|assigned_to', through='learning.AssignmentStudent', blank=True),
        ),
        migrations.AddField(
            model_name='assignment',
            name='course_offering',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Course offering', to='learning.CourseOffering'),
        ),
        migrations.AlterUniqueTogether(
            name='enrollment',
            unique_together=set([('student', 'course_offering')]),
        ),
        migrations.AlterUniqueTogether(
            name='assignmentstudent',
            unique_together=set([('assignment', 'student')]),
        ),
        migrations.RunPython(forwards_func),
    ]
