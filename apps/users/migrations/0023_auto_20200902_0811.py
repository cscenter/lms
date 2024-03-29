# Generated by Django 3.0.9 on 2020-09-02 08:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0022_auto_20200822_1141'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usergroup',
            name='role',
            field=models.PositiveSmallIntegerField(choices=[(1, 'Student'), (2, 'Teacher'), (3, 'Graduate'), (4, 'Co-worker'), (5, 'Curator'), (7, 'Interviewer [Admission]'), (9, 'Project reviewer'), (10, 'Curator of projects'), (11, 'Invited User'), (12, 'Service User')], verbose_name='Role'),
        ),
    ]
