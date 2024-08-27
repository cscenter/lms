# Generated by Django 3.2.18 on 2024-07-20 15:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0042_studentprofile_graduation_year'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprofile',
            name='diploma_degree',
            field=models.CharField(blank=True, choices=[('1', 'bachelor'), ('2', 'speciality'), ('3', 'magistracy'), ('4', 'postgraduate'), ('5', 'secondary professional')], max_length=30, null=True, verbose_name='Degree of diploma'),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='faculty',
            field=models.TextField(blank=True, null=True, verbose_name='Faculty'),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='graduate_without_diploma',
            field=models.BooleanField(default=False, verbose_name='Graduate without diploma'),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='level_of_education_on_admission_other',
            field=models.CharField(blank=True, max_length=12, null=True, verbose_name='StudentInfo|University year (other)'),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='new_track',
            field=models.BooleanField(blank=True, null=True, verbose_name='Alternative track'),
        ),
        migrations.AddField(
            model_name='user',
            name='living_place',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Living Place'),
        ),
        migrations.AlterField(
            model_name='studentprofile',
            name='graduation_year',
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='StudentProfile|graduation_year'),
        ),
    ]