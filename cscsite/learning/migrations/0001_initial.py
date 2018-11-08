# Generated by Django 2.1.3 on 2018-11-08 08:20

import core.db.models
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import learning.models
import model_utils.fields
import sorl.thumbnail.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0002_auto_20180730_1437'),
        ('courses', '0001_initial'),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.CreateModel(
            name='AreaOfStudy',
            fields=[
                ('code', models.CharField(max_length=2, primary_key=True, serialize=False, verbose_name='PK|Code')),
                ('name', models.CharField(max_length=255, verbose_name='AreaOfStudy|Name')),
                ('name_ru', models.CharField(max_length=255, null=True, verbose_name='AreaOfStudy|Name')),
                ('name_en', models.CharField(max_length=255, null=True, verbose_name='AreaOfStudy|Name')),
                ('description', models.TextField(help_text='How to style text read <a href="/commenting-the-right-way/" target="_blank">here</a>. Partially HTML is enabled too.', verbose_name='AreaOfStudy|description')),
                ('description_ru', models.TextField(help_text='How to style text read <a href="/commenting-the-right-way/" target="_blank">here</a>. Partially HTML is enabled too.', null=True, verbose_name='AreaOfStudy|description')),
                ('description_en', models.TextField(help_text='How to style text read <a href="/commenting-the-right-way/" target="_blank">here</a>. Partially HTML is enabled too.', null=True, verbose_name='AreaOfStudy|description')),
            ],
            options={
                'verbose_name': 'Area of study',
                'verbose_name_plural': 'Areas of study',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='AssignmentComment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('text', models.TextField(blank=True, help_text='LaTeX+Markdown is enabled', verbose_name='AssignmentComment|text')),
                ('attached_file', models.FileField(blank=True, upload_to=learning.models.assignmentcomment_upload_to)),
            ],
            options={
                'verbose_name': 'Assignment-comment',
                'verbose_name_plural': 'Assignment-comments',
                'ordering': ['created'],
            },
        ),
        migrations.CreateModel(
            name='AssignmentNotification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('is_about_passed', models.BooleanField(default=False, verbose_name='About passed assignment')),
                ('is_about_creation', models.BooleanField(default=False, verbose_name='About created assignment')),
                ('is_about_deadline', models.BooleanField(default=False, verbose_name='About change of deadline')),
                ('is_unread', models.BooleanField(default=True, verbose_name='Unread')),
                ('is_notified', models.BooleanField(default=False, verbose_name='User is notified')),
            ],
            options={
                'verbose_name': 'Assignment notification',
                'verbose_name_plural': 'Assignment notifications',
                'ordering': ['-created'],
            },
        ),
        migrations.CreateModel(
            name='CourseNewsNotification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('is_unread', models.BooleanField(default=True, verbose_name='Unread')),
                ('is_notified', models.BooleanField(default=False, verbose_name='User is notified')),
            ],
            options={
                'verbose_name': 'Course offering news notification',
                'verbose_name_plural': 'Course offering news notifications',
                'ordering': ['-created'],
            },
        ),
        migrations.CreateModel(
            name='Enrollment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('grade', models.CharField(choices=[('not_graded', 'Not graded'), ('unsatisfactory', 'Enrollment|Unsatisfactory'), ('pass', 'Enrollment|Pass'), ('good', 'Good'), ('excellent', 'Excellent')], default='not_graded', max_length=100, verbose_name='Enrollment|grade')),
                ('grade_changed', model_utils.fields.MonitorField(default=django.utils.timezone.now, monitor='grade', verbose_name='Enrollment|grade changed')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='The student left the course')),
                ('reason_entry', models.TextField(blank=True, verbose_name='Entry reason')),
                ('reason_leave', models.TextField(blank=True, verbose_name='Leave reason')),
            ],
            options={
                'verbose_name': 'Enrollment',
                'verbose_name_plural': 'Enrollments',
                'ordering': ['student', 'course'],
            },
        ),
        migrations.CreateModel(
            name='InternationalSchool',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('name', models.CharField(max_length=255, verbose_name='InternationalSchool|name')),
                ('link', models.URLField(verbose_name='InternationalSchool|Link')),
                ('place', models.CharField(max_length=255, verbose_name='InternationalSchool|place')),
                ('deadline', models.DateField(verbose_name='InternationalSchool|Deadline')),
                ('starts_at', models.DateField(verbose_name='InternationalSchool|Start')),
                ('ends_at', models.DateField(blank=True, null=True, verbose_name='InternationalSchool|End')),
                ('has_grants', models.BooleanField(default=False, verbose_name='InternationalSchool|Grants')),
            ],
            options={
                'verbose_name': 'International school',
                'verbose_name_plural': 'International schools',
                'db_table': 'international_schools',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Internship',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('question', models.CharField(max_length=255, verbose_name='Question')),
                ('answer', models.TextField(verbose_name='Answer')),
                ('sort', models.SmallIntegerField(blank=True, null=True, verbose_name='Sort order')),
            ],
            options={
                'verbose_name': 'Internship',
                'verbose_name_plural': 'Internships',
                'ordering': ['sort'],
            },
        ),
        migrations.CreateModel(
            name='InternshipCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Category name')),
                ('sort', models.SmallIntegerField(blank=True, null=True, verbose_name='Sort order')),
            ],
            options={
                'verbose_name': 'Internship category',
                'verbose_name_plural': 'Internship categories',
                'ordering': ['sort'],
            },
        ),
        migrations.CreateModel(
            name='NonCourseEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('name', models.CharField(max_length=255, verbose_name='CourseClass|Name')),
                ('description', models.TextField(blank=True, help_text='How to style text read <a href="/commenting-the-right-way/" target="_blank">here</a>. Partially HTML is enabled too.', verbose_name='Description')),
                ('date', models.DateField(verbose_name='Date')),
                ('starts_at', models.TimeField(verbose_name='Starts at')),
                ('ends_at', models.TimeField(verbose_name='Ends at')),
            ],
            options={
                'verbose_name': 'Non-course event',
                'verbose_name_plural': 'Non-course events',
                'ordering': ['-date', '-starts_at', 'name'],
            },
        ),
        migrations.CreateModel(
            name='OnlineCourse',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('start', models.DateTimeField(blank=True, null=True, verbose_name='start')),
                ('end', models.DateTimeField(blank=True, null=True, verbose_name='end')),
                ('name', models.CharField(max_length=255, verbose_name='Course|name')),
                ('teachers', models.TextField(help_text='How to style text read <a href="/commenting-the-right-way/" target="_blank">here</a>. Partially HTML is enabled too.', verbose_name='Online Course|teachers')),
                ('description', models.TextField(help_text='How to style text read <a href="/commenting-the-right-way/" target="_blank">here</a>. Partially HTML is enabled too.', verbose_name='Online Course|description')),
                ('link', models.URLField(verbose_name='Online Course|Link')),
                ('photo', sorl.thumbnail.fields.ImageField(blank=True, upload_to='online_courses/', verbose_name='Online Course|photo')),
                ('is_au_collaboration', models.BooleanField(default=False, verbose_name='Collaboration with AY')),
                ('is_self_paced', models.BooleanField(default=False, verbose_name='Without deadlines')),
            ],
            options={
                'verbose_name': 'Online course',
                'verbose_name_plural': 'Online courses',
                'db_table': 'online_courses',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='StudentAssignment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('score', core.db.models.ScoreField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name='Grade')),
                ('score_changed', model_utils.fields.MonitorField(default=django.utils.timezone.now, monitor='score', verbose_name='Assignment|grade changed')),
                ('first_submission_at', models.DateTimeField(editable=False, null=True, verbose_name='Assignment|first_submission')),
                ('last_comment_from', models.PositiveSmallIntegerField(choices=[(0, 'NOBODY'), (1, 'STUDENT'), (2, 'TEACHER')], default=0, editable=False, verbose_name='The author type of the latest comment')),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='courses.Assignment', verbose_name='StudentAssignment|assignment')),
            ],
            options={
                'verbose_name': 'Assignment-student',
                'verbose_name_plural': 'Assignment-students',
                'ordering': ['assignment', 'student'],
            },
        ),
        migrations.CreateModel(
            name='StudyProgram',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('year', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1990)], verbose_name='Year')),
                ('description', models.TextField(blank=True, help_text='How to style text read <a href="/commenting-the-right-way/" target="_blank">here</a>. Partially HTML is enabled too.', null=True, verbose_name='StudyProgram|description')),
                ('area', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='learning.AreaOfStudy', verbose_name='Area of Study')),
                ('city', models.ForeignKey(default='spb', on_delete=django.db.models.deletion.CASCADE, to='core.City', verbose_name='City')),
            ],
            options={
                'verbose_name': 'Study Program',
                'verbose_name_plural': 'Study Programs',
            },
        ),
        migrations.CreateModel(
            name='StudyProgramCourseGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('courses', models.ManyToManyField(help_text='Courses will be grouped with boolean OR', to='courses.MetaCourse', verbose_name='StudyProgramCourseGroup|courses')),
                ('study_program', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='course_groups', to='learning.StudyProgram', verbose_name='Study Program')),
            ],
            options={
                'verbose_name': 'Study Program Course',
                'verbose_name_plural': 'Study Program Courses',
            },
        ),
        migrations.CreateModel(
            name='Useful',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.CharField(max_length=255, verbose_name='Question')),
                ('answer', models.TextField(verbose_name='Answer')),
                ('sort', models.SmallIntegerField(blank=True, null=True, verbose_name='Sort order')),
                ('site', models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='sites.Site', verbose_name='Site')),
            ],
            options={
                'verbose_name': 'Useful',
                'verbose_name_plural': 'Useful',
                'ordering': ['sort'],
            },
        ),
    ]
