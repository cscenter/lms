# Generated by Django 2.2.4 on 2019-08-30 08:14

import core.timezone.models
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('post_office', '0008_attachment_headers'),
        ('courses', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Field',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('label', models.CharField(max_length=255, verbose_name='Label')),
                ('show_label', models.BooleanField(default=True, verbose_name='Show Label')),
                ('input_name', models.CharField(blank=True, max_length=255, verbose_name='Input Name')),
                ('order', models.IntegerField(blank=True, null=True, verbose_name='Order')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('required', models.BooleanField(default=True, verbose_name='Required')),
                ('field_type', models.SmallIntegerField(choices=[(1, 'Single line text'), (2, 'Multi line text'), (3, 'Email'), (13, 'Number'), (14, 'URL'), (4, 'Check box'), (5, 'Check boxes'), (15, 'Check boxes with textarea'), (6, 'Drop down'), (7, 'Multi select'), (8, 'Radio buttons'), (10, 'Date'), (11, 'Date/time')], verbose_name='Field Type')),
                ('placeholder', models.CharField(blank=True, max_length=255, null=True, verbose_name='Placeholder')),
                ('css_class', models.CharField(blank=True, max_length=255, verbose_name='CSS classes')),
                ('visibility', models.SmallIntegerField(choices=[(0, 'Hidden'), (1, 'Visible')], default=1, verbose_name='Visibility')),
                ('help_text', models.TextField(blank=True, null=True, verbose_name='Help Text')),
                ('error_message', models.CharField(blank=True, max_length=255, null=True, verbose_name='Error Message')),
                ('free_answer', models.BooleanField(default=False, verbose_name='Free Answer')),
                ('conditional_logic', models.JSONField(blank=True, help_text='Array of dictionaries with logic rules', null=True, verbose_name='Conditional Logic')),
            ],
            options={
                'verbose_name': 'Field',
                'verbose_name_plural': 'Fields',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Form',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('slug', models.SlugField(verbose_name='Slug')),
                ('status', models.SmallIntegerField(choices=[(0, 'Draft'), (1, 'Published'), (2, 'Template')], default=0, verbose_name='Status')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('response', models.TextField(blank=True, help_text='Shows this message after submitting form.', verbose_name='Response Message')),
            ],
            options={
                'verbose_name': 'Form',
                'verbose_name_plural': 'Forms',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='FormSubmission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('form', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to='surveys.Form')),
            ],
            options={
                'verbose_name': 'Form Submission',
                'verbose_name_plural': 'Form Submissions',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='FieldEntry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_id', models.IntegerField()),
                ('value', models.TextField(null=True)),
                ('is_choice', models.BooleanField(default=False, verbose_name='Is Choice')),
                ('meta', models.JSONField(blank=True, null=True, verbose_name='Meta')),
                ('form', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='entries', to='surveys.Form')),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entries', to='surveys.FormSubmission')),
            ],
            options={
                'verbose_name': 'Form Submission Entry',
                'verbose_name_plural': 'Form Submission Entries',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='FieldChoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('order', models.IntegerField(blank=True, null=True, verbose_name='Order')),
                ('label', models.CharField(max_length=255, verbose_name='Label')),
                ('value', models.CharField(max_length=255, verbose_name='Value')),
                ('default', models.BooleanField(default=False, verbose_name='Default')),
                ('free_answer', models.BooleanField(default=False, help_text='Shows additional input for free answer if user selected this variant.', verbose_name='Free Answer')),
                ('field', models.ForeignKey(limit_choices_to={'field_type__in': [5, 15, 6, 7, 8]}, on_delete=django.db.models.deletion.CASCADE, related_name='choices', to='surveys.Field')),
            ],
            options={
                'verbose_name': 'Field Choice',
                'verbose_name_plural': 'Field Choices',
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='field',
            name='form',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fields', to='surveys.Form'),
        ),
        migrations.CreateModel(
            name='CourseSurvey',
            fields=[
                ('form', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='survey', serialize=False, to='surveys.Form')),
                ('type', models.CharField(choices=[('middle', 'Middle'), ('final', 'Final')], max_length=20, verbose_name='Type')),
                ('expire_at', models.DateTimeField(help_text="With published selected, won't be shown after this time.", verbose_name='Expires on')),
                ('students_notified', models.BooleanField(default=False, editable=False)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='surveys', to='courses.Course')),
                ('email_template', models.ForeignKey(blank=True, help_text='Students will receive notification based on this template after form publication', null=True, on_delete=django.db.models.deletion.CASCADE, to='post_office.EmailTemplate')),
            ],
            options={
                'verbose_name': 'Course Survey',
                'verbose_name_plural': 'Course Surveys',
                'unique_together': {('course', 'type')},
            },
            bases=(core.timezone.models.TimezoneAwareMixin, models.Model),
        ),
    ]
