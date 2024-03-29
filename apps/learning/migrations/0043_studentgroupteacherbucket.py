# Generated by Django 3.2.13 on 2022-12-22 11:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0042_new_assigneemode'),
        ('learning', '0042_enrollmentgradelog'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentGroupTeacherBucket',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='buckets', to='courses.assignment', verbose_name='Assignment')),
                ('groups', models.ManyToManyField(related_name='buckets', to='learning.StudentGroup', verbose_name='Groups')),
                ('teachers', models.ManyToManyField(related_name='buckets', to='courses.CourseTeacher', verbose_name='Teachers')),
            ],
            options={
                'verbose_name': 'Student groups teachers bucket',
                'verbose_name_plural': 'Student groups teachers buckets',
            },
        ),
    ]
