# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import model_utils.fields
import learning.models
import django.utils.timezone
import django.core.validators


def forwards_func(apps, schema_editor):
    Venue = apps.get_model('learning', 'Venue')
    db_alias = schema_editor.connection.alias
    initial_venues = [{"name": "\u041f\u041e\u041c\u0418 \u0420\u0410\u041d",
                       "description": "\u041d\u0430\u0431\u0435\u0440\u0435\u0436\u043d\u0430\u044f \u0440\u0435\u043a\u0438 \u0424\u043e\u043d\u0442\u0430\u043d\u043a\u0438, 27, \u041c\u0440\u0430\u043c\u043e\u0440\u043d\u044b\u0439 \u0437\u0430\u043b (2 \u044d\u0442\u0430\u0436)\r\n\r\n<img src=\"//api-maps.yandex.ru/services/constructor/1.0/static/?sid=hlqT2p1Lqk9imQqe8w2gxQktaxSuP91c&width=600&height=450\" alt=\"\"/>"},
                      {"name": "\u0424\u041c\u041b 239",
                       "description": "\u0424\u0443\u0440\u0448\u0442\u0430\u0442\u0441\u043a\u0430\u044f \u0443\u043b\u0438\u0446\u0430, 9, \u0432\u0442\u043e\u0440\u043e\u0439 \u044d\u0442\u0430\u0436, \u0430\u043a\u0442\u043e\u0432\u044b\u0439 \u0437\u0430\u043b \u043b\u0438\u0431\u043e \u0430\u0443\u0434. 25 (\u0432 \u043a\u043e\u043d\u0446\u0435 \u043a\u043e\u0440\u0438\u0434\u043e\u0440\u0430)\r\n\r\n<img src=\"//api-maps.yandex.ru/services/constructor/1.0/static/?sid=95w30endKrJjcgE7ct5DTGxUgfGuvBgx&width=600&height=450\" alt=\"\"/>"}]
    for page in initial_venues:
        Venue(**page).save(force_insert=True, using=db_alias)



class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Assignment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('deadline_at', models.DateTimeField(verbose_name='Assignment|deadline')),
                ('is_online', models.BooleanField(default=True, verbose_name='Assignment|can be passed online')),
                ('title', models.CharField(max_length=140, verbose_name='Asssignment|name')),
                ('text', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', verbose_name='Assignment|text')),
                ('attached_file', models.FileField(upload_to=learning.models.assignment_upload_to, blank=True)),
                ('grade_min', models.PositiveSmallIntegerField(default=2, verbose_name='Assignment|grade_min', validators=[django.core.validators.MaxValueValidator(1000)])),
                ('grade_max', models.PositiveSmallIntegerField(default=5, verbose_name='Assignment|grade_max', validators=[django.core.validators.MaxValueValidator(1000)])),
            ],
            options={
                'ordering': ['created', 'course_offering'],
                'verbose_name': 'Assignment',
                'verbose_name_plural': 'Assignments',
            },
            bases=(models.Model, object),
        ),
        migrations.CreateModel(
            name='AssignmentComment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('text', models.TextField(help_text='LaTeX+Markdown is enabled', verbose_name='AssignmentComment|text', blank=True)),
                ('attached_file', models.FileField(upload_to=learning.models.assignmentcomment_upload_to, blank=True)),
            ],
            options={
                'ordering': ['created'],
                'verbose_name': 'Assignment-comment',
                'verbose_name_plural': 'Assignment-comments',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AssignmentNotification',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('is_about_passed', models.BooleanField(default=False, verbose_name='About passed assignment')),
                ('is_about_creation', models.BooleanField(default=False, verbose_name='About created assignment')),
                ('is_about_deadline', models.BooleanField(default=False, verbose_name='About change of deadline')),
                ('is_unread', models.BooleanField(default=True, verbose_name='Unread')),
                ('is_notified', models.BooleanField(default=False, verbose_name='User is notified')),
            ],
            options={
                'ordering': ['-created'],
                'verbose_name': 'Assignment notification',
                'verbose_name_plural': 'Assignment notifications',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AssignmentStudent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('grade', models.PositiveSmallIntegerField(null=True, verbose_name='Grade', blank=True)),
                ('grade_changed', model_utils.fields.MonitorField(default=django.utils.timezone.now, verbose_name='Assignment|grade changed', monitor='grade')),
                ('is_passed', models.BooleanField(default=False, help_text="It's online and has comments", verbose_name='Is passed')),
            ],
            options={
                'ordering': ['assignment', 'student'],
                'verbose_name': 'Assignment-student',
                'verbose_name_plural': 'Assignment-students',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('name', models.CharField(max_length=140, verbose_name='Course|name')),
                ('slug', models.SlugField(help_text='Short dash-separated string for human-readable URLs, as in test.com/news/<b>some-news</b>/', unique=True, max_length=70, verbose_name='News|slug')),
                ('description', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', verbose_name='Course|description')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Course',
                'verbose_name_plural': 'Courses',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CourseClass',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('type', model_utils.fields.StatusField(default='lecture', max_length=100, verbose_name='Type', no_check_for_status=True, choices=[('lecture', 'Lecture'), ('seminar', 'Seminar')])),
                ('name', models.CharField(max_length=255, verbose_name='CourseClass|Name')),
                ('description', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', verbose_name='Description', blank=True)),
                ('slides', models.FileField(upload_to=learning.models.courseclass_slides_file_name, verbose_name='Slides', blank=True)),
                ('video', models.TextField(help_text='\u0414\u043e\u0441\u0442\u0443\u043f\u043d\u044b LaTeX+<a href="http://ru.wikipedia.org/wiki/Markdown">Markdown</a>+HTML; \u043f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430, \u0432\u0441\u0442\u0430\u0432\u044c\u0442\u0435 HTML \u0434\u043b\u044f \u0432\u0441\u0442\u0440\u043e\u0435\u043d\u043d\u043e\u0433\u043e \u0432\u0438\u0434\u0435\u043e\u043f\u043b\u0435\u0435\u0440\u0430', verbose_name='CourseClass|Video', blank=True)),
                ('other_materials', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', verbose_name='CourseClass|Other materials', blank=True)),
                ('date', models.DateField(verbose_name='Date')),
                ('starts_at', models.TimeField(verbose_name='Starts at')),
                ('ends_at', models.TimeField(verbose_name='Ends at')),
            ],
            options={
                'ordering': ['-date', 'course_offering', '-starts_at'],
                'verbose_name': 'Class',
                'verbose_name_plural': 'Classes',
            },
            bases=(models.Model, object),
        ),
        migrations.CreateModel(
            name='CourseClassAttachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('material', models.FileField(upload_to='course_class_attachments')),
            ],
            options={
                'ordering': ['course_class', '-created'],
                'verbose_name': 'Class attachment',
                'verbose_name_plural': 'Class attachments',
            },
            bases=(models.Model, object),
        ),
        migrations.CreateModel(
            name='CourseOffering',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('description', models.TextField(help_text='LaTeX+Markdown+HTML is enabled; empty description will be replaced by course description', verbose_name='Description', blank=True)),
                ('is_published_in_video', models.BooleanField(default=False, verbose_name='Published in video section')),
            ],
            options={
                'ordering': ['-semester', 'course__created'],
                'verbose_name': 'Course offering',
                'verbose_name_plural': 'Course offerings',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CourseOfferingNews',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('title', models.CharField(max_length=140, verbose_name='CourseNews|title')),
                ('text', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', verbose_name='CourseNews|text')),
            ],
            options={
                'ordering': ['-created'],
                'verbose_name': 'Course news-singular',
                'verbose_name_plural': 'Course news-plural',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CourseOfferingNewsNotification',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('is_unread', models.BooleanField(default=True, verbose_name='Unread')),
                ('is_notified', models.BooleanField(default=False, verbose_name='User is notified')),
            ],
            options={
                'ordering': ['-created'],
                'verbose_name': 'Course offering news notification',
                'verbose_name_plural': 'Course offering news notifications',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Enrollment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('grade', model_utils.fields.StatusField(default='not_graded', max_length=100, verbose_name='Enrollment|grade', no_check_for_status=True, choices=[('not_graded', 'Not graded'), ('unsatisfactory', 'Enrollment|Unsatisfactory'), ('pass', 'Enrollment|Pass'), ('good', 'Good'), ('excellent', 'Excellent')])),
                ('grade_changed', model_utils.fields.MonitorField(default=django.utils.timezone.now, verbose_name='Enrollment|grade changed', monitor='grade')),
            ],
            options={
                'ordering': ['student', 'course_offering'],
                'verbose_name': 'Enrollment',
                'verbose_name_plural': 'Enrollments',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NonCourseEvent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('name', models.CharField(max_length=255, verbose_name='CourseClass|Name')),
                ('description', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', verbose_name='Description', blank=True)),
                ('date', models.DateField(verbose_name='Date')),
                ('starts_at', models.TimeField(verbose_name='Starts at')),
                ('ends_at', models.TimeField(verbose_name='Ends at')),
            ],
            options={
                'ordering': ['-date', '-starts_at', 'name'],
                'verbose_name': 'Non-course event',
                'verbose_name_plural': 'Non-course events',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Semester',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('year', models.PositiveSmallIntegerField(verbose_name='CSCUser|Year', validators=[django.core.validators.MinValueValidator(1990)])),
                ('type', model_utils.fields.StatusField(default='spring', max_length=100, verbose_name='Semester|type', no_check_for_status=True, choices=[('spring', 'spring'), ('autumn', 'autumn')])),
            ],
            options={
                'ordering': ['-year', 'type'],
                'verbose_name': 'Semester',
                'verbose_name_plural': 'Semesters',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='StudentProject',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('name', models.CharField(max_length=255, verbose_name='StudentProject|Name')),
                ('description', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', verbose_name='Description', blank=True)),
                ('supervisor', models.CharField(help_text='Format: Last_name First_name Patronymic, Organization', max_length=255, verbose_name='StudentProject|Supervisor')),
                ('project_type', models.CharField(max_length=10, verbose_name='StudentProject|Type', choices=[('practice', 'StudentProject|Practice'), ('research', 'StudentProject|Research')])),
                ('presentation', models.FileField(upload_to=learning.models.studentproject_slides_file_name, verbose_name='Presentation', blank=True)),
                ('semesters', models.ManyToManyField(to='learning.Semester', verbose_name='Semesters')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Student project',
                'verbose_name_plural': 'Student projects',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Venue',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=140, verbose_name='Venue|Name')),
                ('address', models.CharField(help_text='Should be resolvable by Google Maps', max_length=500, verbose_name='Venue|Address', blank=True)),
                ('description', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', verbose_name='Description')),
                ('is_preferred', models.BooleanField(default=False, help_text='Will be displayed on top of the venue list', verbose_name='Preferred')),
            ],
            options={
                'ordering': ['-is_preferred', 'name'],
                'verbose_name': 'Venue',
                'verbose_name_plural': 'Venues',
            },
            bases=(models.Model,),
        ),
        migrations.RunPython(forwards_func),
    ]
