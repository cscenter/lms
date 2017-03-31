# -*- coding: utf-8 -*-
# Generated by Django 1.9.12 on 2017-03-31 19:10
from __future__ import unicode_literals

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import jsonfield.fields
import learning.admission.models
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Applicant',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('first_name', models.CharField(max_length=255, verbose_name='First name')),
                ('second_name', models.CharField(max_length=255, verbose_name='Second name')),
                ('last_name', models.CharField(max_length=255, verbose_name='Last name')),
                ('email', models.EmailField(help_text='Applicant|email', max_length=254, verbose_name='Email')),
                ('phone', models.CharField(help_text='Applicant|phone', max_length=42, verbose_name='Contact phone')),
                ('stepic_id', models.PositiveIntegerField(blank=True, help_text='Applicant|stepic_id', null=True, verbose_name='Stepic ID')),
                ('yandex_id', models.CharField(blank=True, help_text='Applicant|yandex_id', max_length=80, null=True, validators=[django.core.validators.RegexValidator(message='Only the part before "@yandex.ru" is expected', regex='^[^@]*$')], verbose_name='Yandex ID')),
                ('yandex_id_normalize', models.CharField(blank=True, help_text='Applicant|yandex_id_normalization', max_length=80, null=True, verbose_name='Yandex ID normalisation')),
                ('github_id', models.CharField(blank=True, help_text='Applicant|github_id', max_length=255, null=True, verbose_name='Github ID')),
                ('university2', models.CharField(help_text='Applicant|university', max_length=255, verbose_name='University')),
                ('university_other', models.CharField(blank=True, help_text='Applicant|university_other', max_length=255, null=True, verbose_name='University (Other)')),
                ('faculty', models.TextField(help_text='Applicant|faculty', verbose_name='Faculty')),
                ('course', models.CharField(choices=[('1', '1 course bachelor, speciality'), ('2', '2 course bachelor, speciality'), ('3', '3 course bachelor, speciality'), ('4', '4 course bachelor, speciality'), ('5', 'last course speciality'), ('6', '1 course magistracy'), ('7', '2 course magistracy'), ('8', 'postgraduate'), ('9', 'graduate')], help_text='Applicant|course', max_length=355, verbose_name='Course')),
                ('graduate_work', models.TextField(blank=True, help_text='Applicant|graduate_work_or_dissertation', null=True, verbose_name='Graduate work')),
                ('experience', models.TextField(blank=True, help_text='Applicant|work_or_study_experience', null=True, verbose_name='Experience')),
                ('has_job', models.CharField(blank=True, help_text='Applicant|has_job', max_length=10, null=True, verbose_name='Do you work?')),
                ('workplace', models.CharField(blank=True, help_text='Applicant|workplace', max_length=255, null=True, verbose_name='Workplace')),
                ('position', models.CharField(blank=True, help_text='Applicant|position', max_length=255, null=True, verbose_name='Position')),
                ('motivation', models.TextField(blank=True, help_text='Applicant|motivation_why', null=True, verbose_name='Your motivation')),
                ('additional_info', models.TextField(blank=True, help_text='Applicant|additional_info', null=True, verbose_name='Additional info from applicant about himself')),
                ('preferred_study_programs', models.CharField(help_text='Applicant|study_program', max_length=255, verbose_name='Study program')),
                ('preferred_study_programs_dm_note', models.TextField(blank=True, help_text='Applicant|study_program_dm', null=True, verbose_name='Study program (DM note)')),
                ('preferred_study_programs_se_note', models.TextField(blank=True, help_text='Applicant|study_program_se', null=True, verbose_name='Study program (SE note)')),
                ('preferred_study_programs_cs_note', models.TextField(blank=True, help_text='Applicant|study_program_cs', null=True, verbose_name='Study program (CS note)')),
                ('where_did_you_learn', models.TextField(help_text='Applicant|where_did_you_learn_about_cs_center', verbose_name='Where did you learn?')),
                ('where_did_you_learn_other', models.CharField(blank=True, max_length=255, null=True, verbose_name='Where did you learn? (other)')),
                ('your_future_plans', models.TextField(blank=True, help_text='Applicant|future_plans', null=True, verbose_name='Future plans')),
                ('admin_note', models.TextField(blank=True, help_text='Applicant|admin_note', null=True, verbose_name='Admin note')),
                ('status', models.CharField(blank=True, choices=[('rejected_test', 'Rejected by test'), ('rejected_exam', 'Rejected by exam'), ('rejected_cheating', 'Cheating'), ('pending', 'Pending'), ('interview_phase', 'Can be interviewed'), ('interview_assigned', 'Interview assigned'), ('interview_completed', 'Interview completed'), ('rejected_interview', 'Rejected by interview'), ('accept', 'Accept'), ('accept_if', 'Accept with condition'), ('volunteer', 'Applicant|Volunteer'), ('they_refused', 'He or she refused')], max_length=20, null=True, verbose_name='Applicant|Status')),
                ('uuid', models.UUIDField(blank=True, editable=False, null=True)),
            ],
            options={
                'verbose_name_plural': 'Applicants',
                'verbose_name': 'Applicant',
            },
        ),
        migrations.CreateModel(
            name='Campaign',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.PositiveSmallIntegerField(default=learning.admission.models.current_year, validators=[django.core.validators.MinValueValidator(2011)], verbose_name='Campaign|Year')),
                ('online_test_max_score', models.SmallIntegerField(verbose_name='Campaign|Test_max_score')),
                ('online_test_passing_score', models.SmallIntegerField(help_text='Campaign|Test_passing_score-help', verbose_name='Campaign|Test_passing_score')),
                ('exam_max_score', models.SmallIntegerField(verbose_name='Campaign|Exam_max_score')),
                ('exam_passing_score', models.SmallIntegerField(help_text='Campaign|Exam_passing_score-help', verbose_name='Campaign|Exam_passing_score')),
                ('current', models.BooleanField(default=False, verbose_name='Current campaign')),
                ('city', models.ForeignKey(default='spb', on_delete=django.db.models.deletion.CASCADE, to='core.City', verbose_name='City')),
            ],
            options={
                'verbose_name_plural': 'Campaigns',
                'verbose_name': 'Campaign',
            },
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('text', models.TextField(blank=True, null=True, verbose_name='Text')),
                ('score', models.SmallIntegerField(validators=[django.core.validators.MinValueValidator(-2), django.core.validators.MaxValueValidator(2)], verbose_name='Score')),
            ],
            options={
                'verbose_name_plural': 'Comments',
                'verbose_name': 'Comment',
            },
        ),
        migrations.CreateModel(
            name='Contest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contest_id', models.CharField(blank=True, help_text='Applicant|yandex_contest_id', max_length=42, null=True, verbose_name='Contest #ID')),
                ('file', models.FileField(blank=True, help_text='Make sure file does not include solutions due to it visible with direct url link', upload_to=learning.admission.models.contest_assignments_upload_to, verbose_name='Assignments in pdf format')),
                ('campaign', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='contests', to='admission.Campaign', verbose_name='Contest|Campaign')),
            ],
            options={
                'verbose_name_plural': 'Contests',
                'verbose_name': 'Contest',
            },
        ),
        migrations.CreateModel(
            name='Exam',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('details', jsonfield.fields.JSONField(blank=True, null=True, verbose_name='Details')),
                ('yandex_contest_id', models.CharField(blank=True, help_text='Applicant|yandex_contest_id', max_length=42, null=True, verbose_name='Contest #ID')),
                ('score', models.PositiveSmallIntegerField(verbose_name='Score')),
                ('applicant', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='exam', to='admission.Applicant', verbose_name='Applicant')),
            ],
            options={
                'verbose_name_plural': 'Exams',
                'verbose_name': 'Exam',
            },
        ),
        migrations.CreateModel(
            name='Interview',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('date', models.DateTimeField(verbose_name='When')),
                ('status', models.CharField(choices=[('approval', 'Approval'), ('deferred', 'Deferred'), ('canceled', 'Canceled'), ('waiting', 'Waiting for interview'), ('completed', 'Completed')], default='approval', max_length=15, verbose_name='Interview|Status')),
                ('note', models.TextField(blank=True, null=True, verbose_name='Note')),
                ('applicant', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='interviews', to='admission.Applicant', verbose_name='Applicant')),
            ],
            options={
                'verbose_name_plural': 'Interviews',
                'verbose_name': 'Interview',
            },
        ),
        migrations.CreateModel(
            name='InterviewAssignment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='InterviewAssignments|name')),
                ('description', models.TextField(help_text='TeX support', verbose_name='Assignment description')),
                ('solution', models.TextField(blank=True, help_text='TeX support', null=True, verbose_name='Assignment solution')),
                ('campaign', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='interview_assignments', to='admission.Campaign', verbose_name='InterviewAssignments|Campaign')),
            ],
            options={
                'verbose_name_plural': 'Interview assignments',
                'verbose_name': 'Interview assignment',
            },
        ),
        migrations.CreateModel(
            name='Test',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('details', jsonfield.fields.JSONField(blank=True, null=True, verbose_name='Details')),
                ('yandex_contest_id', models.CharField(blank=True, help_text='Applicant|yandex_contest_id', max_length=42, null=True, verbose_name='Contest #ID')),
                ('score', models.PositiveSmallIntegerField(verbose_name='Score')),
                ('applicant', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='online_test', to='admission.Applicant', verbose_name='Applicant')),
            ],
            options={
                'verbose_name_plural': 'Testings',
                'verbose_name': 'Testing',
            },
        ),
        migrations.AddField(
            model_name='interview',
            name='assignments',
            field=models.ManyToManyField(blank=True, to='admission.InterviewAssignment', verbose_name='Interview|Assignments'),
        ),
        migrations.AddField(
            model_name='interview',
            name='interviewers',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL, verbose_name='Interview|Interviewers'),
        ),
        migrations.AddField(
            model_name='comment',
            name='interview',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='comments', to='admission.Interview', verbose_name='Interview'),
        ),
        migrations.AddField(
            model_name='comment',
            name='interviewer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='interview_comments', to=settings.AUTH_USER_MODEL, verbose_name='Interviewer'),
        ),
        migrations.AddField(
            model_name='applicant',
            name='campaign',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='applicants', to='admission.Campaign', verbose_name='Applicant|Campaign'),
        ),
        migrations.AddField(
            model_name='applicant',
            name='university',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='applicants', to='core.University', verbose_name='Applicant|University'),
        ),
        migrations.AddField(
            model_name='applicant',
            name='user',
            field=models.OneToOneField(blank=True, null=True, on_delete=models.SET(django.db.models.deletion.SET_NULL), to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='comment',
            unique_together=set([('interview', 'interviewer')]),
        ),
    ]
