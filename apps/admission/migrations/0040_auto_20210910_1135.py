# Generated by Django 3.2.7 on 2021-09-10 11:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0039_auto_20210722_1415'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicant',
            name='email_suspension_details',
            field=models.JSONField(blank=True, editable=False, null=True, verbose_name='Email Address Suspension Details'),
        ),
        migrations.AlterField(
            model_name='acceptance',
            name='confirmation_code',
            field=models.CharField(editable=False, max_length=24, verbose_name='Authorization Code'),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='status',
            field=models.CharField(blank=True, choices=[('rejected_test', 'Rejected by test'), ('permit_to_exam', 'Permitted to the exam'), ('rejected_exam', 'Rejected by exam'), ('rejected_cheating', 'Cheating'), ('pending', 'Pending'), ('interview_phase', 'Can be interviewed'), ('interview_assigned', 'Interview assigned'), ('interview_completed', 'Interview completed'), ('rejected_interview', 'Rejected by interview'), ('rejected_with_bonus', 'Rejected by interview. Offered a bonus'), ('accept_paid', 'Accept on paid'), ('waiting_for_payment', 'Waiting for Payment'), ('accept', 'Accept'), ('accept_if', 'Accept with condition'), ('volunteer', 'Applicant|Volunteer'), ('they_refused', 'He or she refused')], max_length=20, null=True, verbose_name='Applicant|Status'),
        ),
    ]
