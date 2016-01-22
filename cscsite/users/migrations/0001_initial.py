# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import sorl.thumbnail.fields
import django.core.validators
import users.models
import model_utils.fields
import django.utils.timezone
import django.db.models.deletion
from django.conf import settings
import learning.utils


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
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('patronymic', models.CharField(max_length=100, verbose_name='CSCUser|patronymic', blank=True)),
                ('photo', sorl.thumbnail.fields.ImageField(upload_to='photos/', verbose_name='CSCUser|photo', blank=True)),
                ('note', models.TextField(help_text='LaTeX+Markdown is enabled', verbose_name='CSCUser|note', blank=True)),
                ('enrollment_year', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='CSCUser|enrollment year', validators=[django.core.validators.MinValueValidator(1990)])),
                ('graduation_year', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='CSCUser|graduation year', validators=[django.core.validators.MinValueValidator(1990)])),
                ('yandex_id', models.CharField(blank=True, max_length=80, verbose_name='Yandex ID', validators=[django.core.validators.RegexValidator(regex='^[^@]*$', message='Only the part before "@yandex.ru" is expected')])),
                ('github_id', models.CharField(blank=True, max_length=80, verbose_name='Github ID', validators=[django.core.validators.RegexValidator(regex='^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]$')])),
                ('stepic_id', models.PositiveIntegerField(null=True, verbose_name='Stepic ID', blank=True)),
                ('csc_review', models.TextField(help_text='LaTeX+Markdown is enabled', verbose_name='CSC review', blank=True)),
                ('private_contacts', models.TextField(help_text='\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b LaTeX \u0438 Markdown; \u043f\u043e\u043a\u0430\u0437\u044b\u0432\u0430\u0435\u0442\u0441\u044f \u0442\u043e\u043b\u044c\u043a\u043e \u0437\u0430\u043b\u043e\u0433\u0438\u043d\u0435\u043d\u043d\u044b\u043c \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f\u043c', verbose_name='Contact information', blank=True)),
                ('university', models.CharField(max_length=255, verbose_name='University', blank=True)),
                ('phone', models.CharField(max_length=40, verbose_name='Phone', blank=True)),
                ('uni_year_at_enrollment', models.CharField(choices=[('1', '1 course bachelor, speciality'), ('2', '2 course bachelor, speciality'), ('3', '3 course bachelor, speciality'), ('4', '4 course bachelor, speciality'), ('5', 'last course speciality'), ('6', '1 course magistracy'), ('7', '2 course magistracy'), ('8', 'postgraduate'), ('9', 'graduate')], max_length=2, blank=True, help_text='at enrollment', null=True, verbose_name='StudentInfo|University year')),
                ('comment', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a> is enabled', verbose_name='Comment', blank=True)),
                ('comment_changed_at', model_utils.fields.MonitorField(default=django.utils.timezone.now, verbose_name='Comment changed', monitor='comment')),
                ('status', models.CharField(blank=True, max_length=15, verbose_name='Status', choices=[('expelled', 'StudentInfo|Expelled'), ('reinstated', 'StudentInfo|Reinstalled'), ('will_graduate', 'StudentInfo|Will graduate')])),
                ('workplace', models.CharField(max_length=200, verbose_name='Workplace', blank=True)),
                ('comment_last_author', models.ForeignKey(related_name='cscuser_commented', on_delete=django.db.models.deletion.PROTECT, verbose_name='Author of last edit', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('groups', models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Group', blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', verbose_name='groups')),
                ('status_changed_at', users.models.MonitorFKField(monitor='status', log_class=users.models.CSCUserStatusLog, blank=True, to='learning.Semester', help_text='Automatically updated when status changed, but you still can set it manually. Make no sense without status update', null=True, verbose_name='Status changed')),
                ('study_programs', models.ManyToManyField(to='learning.StudyProgram', verbose_name='StudentInfo|Study programs', blank=True)),
                ('user_permissions', models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Permission', blank=True, help_text='Specific permissions for this user.', verbose_name='user permissions')),
            ],
            options={
                'ordering': ['last_name', 'first_name'],
                'verbose_name': 'CSCUser|user',
                'verbose_name_plural': 'CSCUser|users',
            },
            bases=(learning.utils.LearningPermissionsMixin, models.Model),
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
            name='CSCUserStatusLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateField(default=django.utils.timezone.now, verbose_name='created')),
                ('status', models.CharField(max_length=15, verbose_name='Status', choices=[('expelled', 'StudentInfo|Expelled'), ('reinstated', 'StudentInfo|Reinstalled'), ('will_graduate', 'StudentInfo|Will graduate')])),
                ('semester', models.ForeignKey(verbose_name='Semester', to='learning.Semester')),
                ('student', models.ForeignKey(verbose_name='Student', to=settings.AUTH_USER_MODEL)),
            ],
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
                ('teachers', models.CharField(max_length=255, verbose_name='Teachers')),
                ('grade', model_utils.fields.StatusField(default='not_graded', max_length=100, verbose_name='Enrollment|grade', no_check_for_status=True, choices=[('not_graded', 'Not graded'), ('unsatisfactory', 'Enrollment|Unsatisfactory'), ('pass', 'Enrollment|Pass'), ('good', 'Good'), ('excellent', 'Excellent')])),
                ('semester', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Semester', to='learning.Semester')),
                ('student', models.ForeignKey(verbose_name='Student', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'SHAD course record',
                'verbose_name_plural': 'SHAD course records',
            },
        ),
    ]
