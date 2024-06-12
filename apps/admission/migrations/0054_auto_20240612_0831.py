# Generated by Django 3.2.18 on 2024-06-12 08:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0053_alter_applicant_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicant',
            name='interview_format',
            field=models.CharField(blank=True, choices=[('offline', 'Offline'), ('online', 'Online'), ('any', 'Any')], help_text='Applicant|interview_format', max_length=255, verbose_name='Interview Format'),
        ),
        migrations.AddField(
            model_name='applicant',
            name='miss_count',
            field=models.IntegerField(default=0, help_text='Applicant|miss_count', verbose_name='Count of missed interviews'),
        ),
        migrations.AddField(
            model_name='interviewstream',
            name='interviewers_max',
            field=models.IntegerField(blank=True, help_text='Applicant|interviewers_max', null=True, verbose_name='Maximum number of slots preffered by interviewer'),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='status',
            field=models.CharField(blank=True, choices=[('rejected_form_check', 'Rejected by form check'), ('golden_ticket', 'Golden ticket from the previous year'), ('rejected_cheating', 'Cheating'), ('rejected_test', 'Rejected by test'), ('permit_to_olympiad', 'Permitted to the olympiad'), ('permit_to_exam', 'Permitted to the exam'), ('passed_olympiad', 'Passed the olympiad'), ('failed_olympiad', 'Failed the olympiad, will write the exam'), ('reject_exam_cheater', 'Rejected by exam cheating'), ('rejected_exam', 'Rejected by exam'), ('passed_exam', 'Passed the exam'), ('rejected_interview', 'Rejected by interview'), ('rejected_with_bonus', 'Rejected by interview. Offered a bonus'), ('accept', 'Accept'), ('accept_if', 'Accept with condition'), ('they_refused', 'He or she refused'), ('permit_to_intensive', 'Permitted to the intensive'), ('pending', 'Pending'), ('rejected_intensive', 'Rejected by intensive'), ('rejected_intensive_bonus', 'Rejected by intensive. Offered a bonus'), ('accept_paid', 'Accept on paid')], max_length=30, null=True, verbose_name='Applicant|Status'),
        ),
        migrations.AlterField(
            model_name='interview',
            name='section',
            field=models.CharField(choices=[('all_in_1', 'Common Section'), ('math', 'Math'), ('code', 'Code'), ('math_code', 'Math and code'), ('mv', 'Motivation')], max_length=15, verbose_name='Interview|Section'),
        ),
        migrations.AlterField(
            model_name='interviewstream',
            name='section',
            field=models.CharField(choices=[('all_in_1', 'Common Section'), ('math', 'Math'), ('code', 'Code'), ('math_code', 'Math and code'), ('mv', 'Motivation')], max_length=15, verbose_name='Interview|Section'),
        ),
    ]
