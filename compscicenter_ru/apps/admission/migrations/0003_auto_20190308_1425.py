# Generated by Django 2.1.5 on 2019-03-08 14:25

from django.db import migrations, models
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0002_auto_20190109_1344'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicant',
            name='living_place',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Living Place'),
        ),
        migrations.AddField(
            model_name='applicant',
            name='online_education_experience',
            field=models.TextField(blank=True, null=True, default='', help_text='Applicant|online_education_experience', verbose_name='Online Education Exp'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='applicant',
            name='probability',
            field=models.TextField(blank=True, help_text='Applicant|probability', null=True, verbose_name='Probability'),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='preferred_study_programs',
            field=multiselectfield.db.fields.MultiSelectField(choices=[('ds', 'Data Science (Анализ данных)'), ('cs', 'Computer Science (Современная информатика)'), ('se', 'Software Engineering (Разработка ПО)')], help_text='Applicant|study_program', max_length=255, verbose_name='Study program'),
        ),
    ]
