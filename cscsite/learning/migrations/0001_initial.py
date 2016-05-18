# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import bitfield.models
import sorl.thumbnail.fields
import learning.utils
import model_utils.fields
import learning.models
import django.utils.timezone
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
        ('core', '0001_initial'),
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
            name='AssignmentAttachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('attachment', models.FileField(upload_to=learning.models.assignmentattach_upload_to)),
            ],
            options={
                'ordering': ['assignment', '-created'],
                'verbose_name': 'Assignment attachment',
                'verbose_name_plural': 'Assignment attachments',
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
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('name', models.CharField(max_length=140, verbose_name='Course|name')),
                ('name_ru', models.CharField(max_length=140, null=True, verbose_name='Course|name')),
                ('name_en', models.CharField(max_length=140, null=True, verbose_name='Course|name')),
                ('slug', models.SlugField(help_text='Short dash-separated string for human-readable URLs, as in test.com/news/<b>some-news</b>/', unique=True, max_length=70, verbose_name='News|slug')),
                ('description', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', verbose_name='Course|description')),
                ('description_ru', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', null=True, verbose_name='Course|description')),
                ('description_en', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', null=True, verbose_name='Course|description')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Course',
                'verbose_name_plural': 'Courses',
            },
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
                ('slides_url', models.URLField(verbose_name='SlideShare URL', blank=True)),
                ('video_url', models.URLField(help_text='Both YouTube and Yandex Video are supported', verbose_name='Video URL', blank=True)),
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
                ('description_ru', models.TextField(help_text='LaTeX+Markdown+HTML is enabled; empty description will be replaced by course description', null=True, verbose_name='Description', blank=True)),
                ('description_en', models.TextField(help_text='LaTeX+Markdown+HTML is enabled; empty description will be replaced by course description', null=True, verbose_name='Description', blank=True)),
                ('survey_url', models.URLField(help_text='Link to Survey', verbose_name='Survey URL', blank=True)),
                ('is_published_in_video', models.BooleanField(default=False, verbose_name='Published in video section')),
                ('is_open', models.BooleanField(default=False, help_text='This course offering will be available on ComputerScience Club website so anyone can join', verbose_name='Open course offering')),
                ('is_completed', models.BooleanField(default=False, verbose_name='Course already completed')),
                ('language', models.CharField(default=b'ru', max_length=5, db_index=True, choices=[(b'ru', b'Russian'), (b'en', b'English')])),
            ],
            options={
                'ordering': ['-semester', 'course__created'],
                'verbose_name': 'Course offering',
                'verbose_name_plural': 'Course offerings',
            },
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
        ),
        migrations.CreateModel(
            name='CourseOfferingTeacher',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('roles', bitfield.models.BitField((('lecturer', 'Lecturer'), ('reviewer', 'Reviewer')), default=1)),
            ],
            options={
                'verbose_name': 'Course Offering teacher',
                'verbose_name_plural': 'Course Offering teachers',
            },
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
        ),
        migrations.CreateModel(
            name='InternationalSchool',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('name', models.CharField(max_length=255, verbose_name='InternationalSchool|name')),
                ('link', models.URLField(verbose_name='InternationalSchool|Link')),
                ('place', models.CharField(max_length=255, verbose_name='InternationalSchool|place')),
                ('deadline', models.DateField(verbose_name='InternationalSchool|Deadline')),
                ('starts_at', models.DateField(verbose_name='InternationalSchool|Start')),
                ('ends_at', models.DateField(verbose_name='InternationalSchool|End')),
                ('has_grants', models.BooleanField(default=False, verbose_name='InternationalSchool|Grants')),
            ],
            options={
                'ordering': ['name'],
                'db_table': 'international_schools',
                'verbose_name': 'International school',
                'verbose_name_plural': 'International schools',
            },
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
        ),
        migrations.CreateModel(
            name='OnlineCourse',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('start', models.DateTimeField(null=True, verbose_name='start', blank=True)),
                ('end', models.DateTimeField(null=True, verbose_name='end', blank=True)),
                ('name', models.CharField(max_length=255, verbose_name='Course|name')),
                ('teachers', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', verbose_name='Online Course|teachers')),
                ('description', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', verbose_name='Online Course|description')),
                ('link', models.URLField(verbose_name='Online Course|Link')),
                ('photo', sorl.thumbnail.fields.ImageField(upload_to='online_courses/', verbose_name='Online Course|photo', blank=True)),
                ('is_au_collaboration', models.BooleanField(default=False, verbose_name='Collaboration with AY')),
                ('is_self_paced', models.BooleanField(default=False, verbose_name='Without deadlines')),
            ],
            options={
                'ordering': ['name'],
                'db_table': 'online_courses',
                'verbose_name': 'Online course',
                'verbose_name_plural': 'Online courses',
            },
        ),
        migrations.CreateModel(
            name='Semester',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('year', models.PositiveSmallIntegerField(verbose_name='Year', validators=[django.core.validators.MinValueValidator(1990)])),
                ('type', model_utils.fields.StatusField(default='spring', max_length=100, verbose_name='Semester|type', no_check_for_status=True, choices=[('spring', 'spring'), ('summer', 'summer'), ('autumn', 'autumn')])),
                ('enroll_before', models.DateField(help_text='Students can enroll on or leave the course before this date (inclusive)', null=True, verbose_name='Enroll before', blank=True)),
                ('index', models.PositiveSmallIntegerField(help_text='System field. Do not manually edit', verbose_name='Semester index', editable=False)),
            ],
            options={
                'ordering': ['-year', 'type'],
                'verbose_name': 'Semester',
                'verbose_name_plural': 'Semesters',
            },
        ),
        migrations.CreateModel(
            name='StudentAssignment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('grade', models.PositiveSmallIntegerField(null=True, verbose_name='Grade', blank=True)),
                ('grade_changed', model_utils.fields.MonitorField(default=django.utils.timezone.now, verbose_name='Assignment|grade changed', monitor='grade')),
                ('is_passed', models.BooleanField(default=False, help_text="It's online and has comments", verbose_name='Is passed')),
                ('last_commented', models.DateTimeField(null=True, verbose_name='Last comment date', blank=True)),
            ],
            options={
                'ordering': ['assignment', 'student'],
                'verbose_name': 'Assignment-student',
                'verbose_name_plural': 'Assignment-students',
            },
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
                ('is_external', models.BooleanField(default=False, verbose_name='External project')),
                ('semester', models.ForeignKey(verbose_name='Semester', to='learning.Semester')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Student project',
                'verbose_name_plural': 'Student projects',
            },
            bases=(models.Model),
        ),
        migrations.CreateModel(
            name='StudyProgram',
            fields=[
                ('code', models.CharField(max_length=2, serialize=False, verbose_name='PK|Code', primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='StudyProgram|Name')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Study program',
                'verbose_name_plural': 'Study programs',
            },
        ),
        migrations.CreateModel(
            name='Venue',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=140, verbose_name='Venue|Name')),
                ('address', models.CharField(help_text='Should be resolvable by Google Maps', max_length=500, verbose_name='Venue|Address', blank=True)),
                ('description', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', verbose_name='Description')),
                ('is_preferred', models.BooleanField(default=False, help_text='Will be displayed on top of the venue list', verbose_name='Preferred')),
                ('city', models.ForeignKey(default=b'RU SPB', blank=True, to='core.City', null=True)),
                ('sites', models.ManyToManyField(to='sites.Site')),
            ],
            options={
                'ordering': ['-is_preferred', 'name'],
                'verbose_name': 'Venue',
                'verbose_name_plural': 'Venues',
            },
        ),
    ]
