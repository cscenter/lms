# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sorl.thumbnail.fields
import model_utils.fields
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
import django.core.validators


def forwards_func(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    db_alias = schema_editor.connection.alias
    Group(name="Student").save(force_insert=True, using=db_alias)
    Group(name="Teacher").save(force_insert=True, using=db_alias)
    Group(name="Graduate").save(force_insert=True, using=db_alias)


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
        ('learning', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CSCUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(null=True, verbose_name='last login', blank=True)),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, max_length=30, validators=[django.core.validators.RegexValidator('^[\\w.@+-]+$', 'Enter a valid username. This value may contain only letters, numbers and @/./+/-/_ characters.', 'invalid')], help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.', unique=True, verbose_name='username')),
                ('first_name', models.CharField(max_length=30, verbose_name='first name', blank=True)),
                ('last_name', models.CharField(max_length=30, verbose_name='last name', blank=True)),
                ('email', models.EmailField(max_length=254, verbose_name='email address', blank=True)),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('gender', models.CharField(max_length=1, verbose_name='Gender', choices=[('M', 'Male'), ('F', 'Female')])),
                ('patronymic', models.CharField(max_length=100, verbose_name='CSCUser|patronymic', blank=True)),
                ('photo', sorl.thumbnail.fields.ImageField(upload_to='photos/', verbose_name='CSCUser|photo', blank=True)),
                ('note', models.TextField(help_text='LaTeX+Markdown is enabled', verbose_name='CSCUser|note', blank=True)),
                ('enrollment_year', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='CSCUser|enrollment year', validators=[django.core.validators.MinValueValidator(1990)])),
                ('graduation_year', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='CSCUser|graduation year', validators=[django.core.validators.MinValueValidator(1990)])),
                ('yandex_id', models.CharField(blank=True, max_length=80, verbose_name='Yandex ID', validators=[django.core.validators.RegexValidator(regex='^[^@]*$', message='Only the part before "@yandex.ru" is expected')])),
                ('github_id', models.CharField(blank=True, max_length=80, verbose_name='Github ID', validators=[django.core.validators.RegexValidator(regex='^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]$')])),
                ('stepic_id', models.PositiveIntegerField(null=True, verbose_name='Stepic ID', blank=True)),
                ('csc_review', models.TextField(help_text='LaTeX+Markdown is enabled', verbose_name='CSC review', blank=True)),
                ('private_contacts', models.TextField(help_text='LaTeX+Markdown is enabled; will be shown only to logged-in users', verbose_name='Contact information', blank=True)),
                ('is_center_student', models.BooleanField(default=False, help_text="Students without this flag belong to CSClub only and can't enroll to CSCenter's courses", verbose_name='Student of CSCenter')),
                ('university', models.CharField(max_length=140, verbose_name='University', blank=True)),
                ('phone', models.CharField(max_length=40, verbose_name='Phone', blank=True)),
                ('uni_year_at_enrollment', models.PositiveSmallIntegerField(blank=True, help_text='at enrollment', null=True, verbose_name='StudentInfo|University year', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(10)])),
                ('comment', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a> is enabled', verbose_name='Comment', blank=True)),
                ('comment_changed_at', model_utils.fields.MonitorField(default=django.utils.timezone.now, verbose_name='Comment changed', monitor='comment')),
                ('nondegree', models.BooleanField(default=False, verbose_name='Non-degree student')),
                ('status', models.CharField(blank=True, max_length=15, verbose_name='Status', choices=[('graduate', 'Graduate'), ('expelled', 'StudentInfo|Expelled'), ('reinstated', 'StudentInfo|Reinstalled'), ('will_graduate', 'StudentInfo|Will graduate')])),
                ('workplace', models.CharField(max_length=200, verbose_name='Workplace', blank=True)),
                ('comment_last_author', models.ForeignKey(related_name='cscuser_commented', on_delete=django.db.models.deletion.PROTECT, verbose_name='Author of last edit', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('groups', models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Group', blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', verbose_name='groups')),
                ('study_programs', models.ManyToManyField(to='learning.StudyProgram', verbose_name='StudentInfo|Study programs', blank=True)),
                ('user_permissions', models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Permission', blank=True, help_text='Specific permissions for this user.', verbose_name='user permissions')),
            ],
            options={
                'ordering': ['last_name', 'first_name'],
                'verbose_name': 'CSCUser|user',
                'verbose_name_plural': 'CSCUser|users',
            },
        ),
        migrations.CreateModel(
            name='CSCUserReference',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('signature', models.CharField(max_length=255, verbose_name='Reference|signature')),
                ('note', models.TextField(verbose_name='Reference|note', blank=True)),
                ('student', models.ForeignKey(verbose_name='Student', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['signature'],
                'verbose_name': 'User reference record',
                'verbose_name_plural': 'User reference records',
            },
        ),
        migrations.CreateModel(
            name='OnlineCourseRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('name', models.CharField(max_length=255, verbose_name='Course|name')),
                ('student', models.ForeignKey(verbose_name='Student', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Online course record',
                'verbose_name_plural': 'Online course records',
            },
        ),
        migrations.CreateModel(
            name='SHADCourseRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('name', models.CharField(max_length=255, verbose_name='Course|name')),
                ('grade', models.PositiveSmallIntegerField(blank=True, help_text='from 2 to 5, inclusive', null=True, verbose_name='Grade', validators=[django.core.validators.MinValueValidator(2), django.core.validators.MaxValueValidator(5)])),
                ('student', models.ForeignKey(verbose_name='Student', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'SHAD course record',
                'verbose_name_plural': 'SHAD course records',
            },
        ),
        migrations.RunPython(forwards_func)
    ]
