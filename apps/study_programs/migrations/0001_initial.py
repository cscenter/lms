# Generated by Django 2.2.4 on 2019-08-30 08:14

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import sorl.thumbnail.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('courses', '0001_initial'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AcademicDiscipline',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=2, verbose_name='PK|Code')),
                ('name', models.CharField(max_length=255, verbose_name='AreaOfStudy|Name')),
                ('name_ru', models.CharField(max_length=255, null=True, verbose_name='AreaOfStudy|Name')),
                ('name_en', models.CharField(max_length=255, null=True, verbose_name='AreaOfStudy|Name')),
                ('cover', sorl.thumbnail.fields.ImageField(blank=True, upload_to='academic_disciplines/', verbose_name='AcademicDiscipline|cover')),
                ('icon', models.FileField(blank=True, upload_to='academic_disciplines/', verbose_name='AcademicDiscipline|icon')),
                ('description', models.TextField(verbose_name='AreaOfStudy|description')),
                ('description_ru', models.TextField(null=True, verbose_name='AreaOfStudy|description')),
                ('description_en', models.TextField(null=True, verbose_name='AreaOfStudy|description')),
            ],
            options={
                'verbose_name': 'Area of study',
                'verbose_name_plural': 'Areas of study',
                'db_table': 'areas_of_study',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='StudyProgram',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('year', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1990)], verbose_name='Year')),
                ('is_active', models.BooleanField(default=True, help_text='Show on syllabus page. Other activity flags for selected branch and academic discipline will be deactivated.', verbose_name='Activity')),
                ('description', models.TextField(blank=True, null=True, verbose_name='StudyProgram|description')),
                ('academic_discipline', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_query_name='study_program', to='study_programs.AcademicDiscipline', verbose_name='Area of Study')),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='study_programs', to='core.Branch', verbose_name='Branch')),
            ],
            options={
                'verbose_name': 'Study Program',
                'verbose_name_plural': 'Study Programs',
                'db_table': 'study_programs',
            },
        ),
        migrations.CreateModel(
            name='StudyProgramCourseGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('courses', models.ManyToManyField(help_text='Courses will be grouped with boolean OR', to='courses.MetaCourse', verbose_name='StudyProgramCourseGroup|courses')),
                ('study_program', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='course_groups', to='study_programs.StudyProgram', verbose_name='Study Program')),
            ],
            options={
                'verbose_name': 'Study Program Course',
                'verbose_name_plural': 'Study Program Courses',
                'db_table': 'study_programs_groups',
            },
        ),
    ]
