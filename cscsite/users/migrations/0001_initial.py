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
    Group(id=1, name="Student").save(force_insert=True, using=db_alias)
    Group(id=2, name="Teacher").save(force_insert=True, using=db_alias)
    Group(id=3, name="Graduate").save(force_insert=True, using=db_alias)


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CSCUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.', unique=True, max_length=30, verbose_name='username', validators=[django.core.validators.RegexValidator('^[\\w.@+-]+$', 'Enter a valid username.', 'invalid')])),
                ('first_name', models.CharField(max_length=30, verbose_name='first name', blank=True)),
                ('last_name', models.CharField(max_length=30, verbose_name='last name', blank=True)),
                ('email', models.EmailField(max_length=75, verbose_name='email address', blank=True)),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('patronymic', models.CharField(max_length=100, verbose_name='CSCUser|patronymic', blank=True)),
                ('photo', sorl.thumbnail.fields.ImageField(upload_to='photos/', verbose_name='CSCUser|photo', blank=True)),
                ('note', models.TextField(help_text='LaTeX+Markdown is enabled', verbose_name='CSCUser|note', blank=True)),
                ('enrollment_year', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='CSCUser|enrollment year', validators=[django.core.validators.MinValueValidator(1990)])),
                ('graduation_year', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='CSCUser|graduation year', validators=[django.core.validators.MinValueValidator(1990)])),
                ('yandex_id', models.CharField(blank=True, max_length=80, verbose_name='Yandex ID', validators=[django.core.validators.RegexValidator(regex='^[^@]*$', message='Only the part before "@yandex.ru" is expected')])),
                ('stepic_id', models.PositiveIntegerField(null=True, verbose_name='Stepic ID', blank=True)),
                ('csc_review', models.TextField(help_text='LaTeX+Markdown is enabled', verbose_name='CSC review', blank=True)),
                ('private_contacts', models.TextField(help_text='\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b LaTeX \u0438 Markdown; \u043f\u043e\u043a\u0430\u0437\u044b\u0432\u0430\u0435\u0442\u0441\u044f \u0442\u043e\u043b\u044c\u043a\u043e \u0437\u0430\u043b\u043e\u0433\u0438\u043d\u0435\u043d\u043d\u044b\u043c \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f\u043c', verbose_name='Contact information', blank=True)),
                ('groups', models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Group', blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of his/her group.', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Permission', blank=True, help_text='Specific permissions for this user.', verbose_name='user permissions')),
            ],
            options={
                'ordering': ['last_name', 'first_name'],
                'verbose_name': 'CSCUser|user',
                'verbose_name_plural': 'CSCUser|users',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='StudentInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('university', models.CharField(max_length=140, verbose_name='University', blank=True)),
                ('phone', models.CharField(max_length=40, verbose_name='Phone', blank=True)),
                ('uni_year_at_enrollment', models.PositiveSmallIntegerField(blank=True, help_text='at enrollment', null=True, verbose_name='StudentInfo|University year', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(10)])),
                ('comment', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a> is enabled', verbose_name='Comment', blank=True)),
                ('comment_changed', model_utils.fields.MonitorField(default=django.utils.timezone.now, verbose_name='Comment changed', monitor='comment')),
                ('nondegree', models.BooleanField(default=False, verbose_name='Non-degree student')),
                ('status', models.CharField(blank=True, max_length=15, verbose_name='Status', choices=[('graduate', 'Graduate'), ('expelled', 'StudentInfo|Expelled'), ('reinstated', 'StudentInfo|Reinstalled'), ('will_graduate', 'StudentInfo|Will graduate')])),
                ('study_program', models.CharField(blank=True, max_length=2, verbose_name='StudentInfo|Study program', choices=[('dm', 'Data mining'), ('cs', 'Computer Science'), ('se', 'Software Engineering')])),
                ('online_courses', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a> is enabled', verbose_name='Online courses', blank=True)),
                ('shad_courses', models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a> is enabled', verbose_name='School of Data Analysis courses', blank=True)),
                ('workplace', models.CharField(max_length=200, verbose_name='Workplace', blank=True)),
                ('comment_last_author', models.ForeignKey(related_name='studentinfo_commented', on_delete=django.db.models.deletion.PROTECT, verbose_name='Author of last edit', to=settings.AUTH_USER_MODEL)),
                ('student', models.OneToOneField(verbose_name='Student', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['student'],
                'verbose_name': 'Student info record',
                'verbose_name_plural': 'Student info records',
            },
            bases=(models.Model,),
        ),
        migrations.RunPython(forwards_func),
        # NOTE(Dmitry): this is needed to move forward "autoincrementing"
        #               counters that are used to give new groups/etc
        #               unique IDs
        migrations.RunSQL("""
BEGIN;
SELECT setval(pg_get_serial_sequence('"auth_permission"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "auth_permission";
SELECT setval(pg_get_serial_sequence('"auth_group_permissions"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "auth_group_permissions";
SELECT setval(pg_get_serial_sequence('"auth_group"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "auth_group";
COMMIT;
        """)
    ]
