# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
import model_utils.fields
import jsonfield.fields
import django.db.models.deletion
from django.conf import settings
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Applicant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('first_name', models.CharField(max_length=255, verbose_name='First name')),
                ('second_name', models.CharField(max_length=255, verbose_name='Second name')),
                ('last_name', models.CharField(max_length=255, verbose_name='Last name')),
                ('email', models.EmailField(help_text='Applicant|email', max_length=254, verbose_name='Email')),
                ('phone', models.CharField(help_text='Applicant|phone', max_length=42, verbose_name='Last name')),
                ('stepic_id', models.PositiveIntegerField(help_text='Applicant|stepic_id', null=True, verbose_name='Stepic ID', blank=True)),
                ('yandex_id', models.CharField(help_text='Applicant|yandex_id', max_length=80, verbose_name='Yandex ID', validators=[django.core.validators.RegexValidator(regex='^[^@]*$', message='Only the part before "@yandex.ru" is expected')])),
                ('university', models.CharField(help_text='Applicant|university', max_length=255, verbose_name='University')),
                ('faculty', models.CharField(help_text='Applicant|faculty', max_length=255, verbose_name='Faculty')),
                ('course', models.CharField(help_text='Applicant|course', max_length=255, verbose_name='Course')),
                ('graduate_work', models.TextField(help_text='Applicant|graduate_work', null=True, verbose_name='Graduate work', blank=True)),
                ('experience', models.TextField(help_text='Applicant|experience', verbose_name='Experience')),
                ('motivation', models.TextField(help_text='Applicant|motivation', verbose_name='Your motivation')),
                ('additional_info', models.TextField(help_text='Applicant|additional_info', null=True, verbose_name='Additional info from applicant about himself', blank=True)),
                ('preferred_study_programs', models.TextField(help_text='Applicant|study_program', verbose_name='Study program')),
                ('where_did_you_learn', models.CharField(help_text='Applicant|where_did_you_learn', max_length=255, verbose_name='Where did you learn?')),
                ('admin_note', models.TextField(help_text='Applicant|admin_note', null=True, verbose_name='Admin note', blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Campaign',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=140, verbose_name='Campaign|Campaign_name')),
            ],
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('text', models.TextField(null=True, verbose_name='Text', blank=True)),
                ('score', models.DecimalField(verbose_name='Score', max_digits=2, decimal_places=1)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Exam',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('details', jsonfield.fields.JSONField(null=True, blank=True)),
                ('yandex_contest_id', models.CharField(help_text='Applicant|yandex_contest_id', max_length=42, null=True, verbose_name='Contest #ID', blank=True)),
                ('score', models.DecimalField(verbose_name='Score', max_digits=3, decimal_places=1)),
                ('applicant', models.ForeignKey(related_name='exams', on_delete=django.db.models.deletion.PROTECT, verbose_name='Applicant', to='admission.Applicant')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Interview',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('date', models.DateTimeField(verbose_name='When')),
                ('decision', models.CharField(default='waiting', max_length=10, verbose_name='Interview|Decision', choices=[('waiting', 'Waiting for interview'), ('canceled', 'Canceled'), ('accept', 'Accept'), ('decline', 'Decline'), ('volunteer', 'Volunteer')])),
                ('decision_comment', models.TextField(null=True, verbose_name='Decision summary', blank=True)),
                ('applicant', models.ForeignKey(related_name='interviews', on_delete=django.db.models.deletion.PROTECT, verbose_name='Applicant', to='admission.Applicant')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Interviewer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('user', models.ForeignKey(verbose_name='Interviewer|user', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Test',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('details', jsonfield.fields.JSONField(null=True, blank=True)),
                ('yandex_contest_id', models.CharField(help_text='Applicant|yandex_contest_id', max_length=42, null=True, verbose_name='Contest #ID', blank=True)),
                ('score', models.DecimalField(verbose_name='Score', max_digits=3, decimal_places=1)),
                ('applicant', models.ForeignKey(related_name='tests', on_delete=django.db.models.deletion.PROTECT, verbose_name='Applicant', to='admission.Applicant')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='comment',
            name='interview',
            field=models.ForeignKey(related_name='comments', on_delete=django.db.models.deletion.PROTECT, verbose_name='Interview', to='admission.Interview'),
        ),
        migrations.AddField(
            model_name='comment',
            name='interviewer',
            field=models.ForeignKey(related_name='comments', on_delete=django.db.models.deletion.PROTECT, to='admission.Interviewer'),
        ),
        migrations.AddField(
            model_name='applicant',
            name='campaign',
            field=models.ForeignKey(related_name='applicants', on_delete=django.db.models.deletion.PROTECT, verbose_name='Applicant|Campaign', to='admission.Campaign'),
        ),
    ]
