# Generated by Django 3.2.18 on 2025-04-15 17:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0061_alter_applicant_mipt_grades_file'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='applicant',
            unique_together=set(),
        ),
    ]
