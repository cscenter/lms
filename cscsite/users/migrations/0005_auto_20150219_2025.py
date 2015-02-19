# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
import model_utils.fields
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0004_data_add_studyprograms'),
        ('users', '0004_onlinecourserecord_shadcourserecord'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='studentinfo',
            name='comment_last_author',
        ),
        migrations.RemoveField(
            model_name='studentinfo',
            name='student',
        ),
        migrations.RemoveField(
            model_name='studentinfo',
            name='study_programs',
        ),
        migrations.RemoveField(
            model_name='onlinecourserecord',
            name='student_info',
        ),
        migrations.RemoveField(
            model_name='shadcourserecord',
            name='student_info',
        ),
        migrations.DeleteModel(
            name='StudentInfo',
        ),
        migrations.AddField(
            model_name='cscuser',
            name='comment',
            field=models.TextField(help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a> is enabled', verbose_name='Comment', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='cscuser',
            name='comment_changed',
            field=model_utils.fields.MonitorField(default=django.utils.timezone.now, verbose_name='Comment changed', monitor='comment'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='cscuser',
            name='comment_last_author',
            field=models.ForeignKey(related_name='cscuser_commented', on_delete=django.db.models.deletion.PROTECT, verbose_name='Author of last edit', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='cscuser',
            name='nondegree',
            field=models.BooleanField(default=False, verbose_name='Non-degree student'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='cscuser',
            name='phone',
            field=models.CharField(max_length=40, verbose_name='Phone', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='cscuser',
            name='status',
            field=models.CharField(blank=True, max_length=15, verbose_name='Status', choices=[('graduate', 'Graduate'), ('expelled', 'StudentInfo|Expelled'), ('reinstated', 'StudentInfo|Reinstalled'), ('will_graduate', 'StudentInfo|Will graduate')]),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='cscuser',
            name='study_programs',
            field=models.ManyToManyField(to='learning.StudyProgram', verbose_name='StudentInfo|Study programs', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='cscuser',
            name='uni_year_at_enrollment',
            field=models.PositiveSmallIntegerField(blank=True, help_text='at enrollment', null=True, verbose_name='StudentInfo|University year', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(10)]),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='cscuser',
            name='university',
            field=models.CharField(max_length=140, verbose_name='University', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='cscuser',
            name='workplace',
            field=models.CharField(max_length=200, verbose_name='Workplace', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='onlinecourserecord',
            name='student',
            field=models.ForeignKey(verbose_name='Student', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='shadcourserecord',
            name='student',
            field=models.ForeignKey(verbose_name='Student', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
    ]
