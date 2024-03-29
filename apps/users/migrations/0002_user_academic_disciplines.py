# Generated by Django 2.2.5 on 2019-09-13 13:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('study_programs', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='academic_disciplines',
            field=models.ManyToManyField(blank=True, help_text='Academic disciplines from which student plans to graduate', to='study_programs.AcademicDiscipline', verbose_name='Fields of study'),
        ),
    ]
