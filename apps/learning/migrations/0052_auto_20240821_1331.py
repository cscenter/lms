# Generated by Django 3.2.18 on 2024-08-21 13:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0051_auto_20240802_2000'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseinvitation',
            name='enrollment_type',
            field=models.CharField(choices=[('Regular', 'InvitationEnrollmentTypes|Regular'), ('lections', 'InvitationEnrollmentTypes|Lections'), ('Any', 'InvitationEnrollmentTypes|Any')], default='Any', max_length=100, verbose_name='Enrollment|type'),
        ),
        migrations.AddField(
            model_name='enrollment',
            name='type',
            field=models.CharField(choices=[('Regular', 'EnrollmentTypes|Regular'), ('lections', 'EnrollmentTypes|Lections')], default='Regular', max_length=100, verbose_name='Enrollment|type'),
        ),
    ]
