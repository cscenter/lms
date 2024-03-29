# Generated by Django 2.2.10 on 2020-04-21 11:54

import admission.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("admission", "0006_auto_20200330_1836"),
    ]

    operations = [
        migrations.AddField(
            model_name="campaign",
            name="template_exam_invitation",
            field=models.CharField(
                blank=True,
                help_text="Template name for the exam registration email",
                max_length=255,
                validators=[admission.models.validate_email_template_name],
                verbose_name="Exam Invitation Email Template",
            ),
        ),
        migrations.AlterField(
            model_name="exam",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "Not registered in the contest"),
                    ("registered", "Syncing with a contest"),
                    ("manual", "Manual score input"),
                ],
                default="new",
                help_text="Choose `manual score input` to avoid synchronization with contest results",
                max_length=15,
                verbose_name="Status",
            ),
        ),
        migrations.AlterField(
            model_name="test",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "Not registered in the contest"),
                    ("registered", "Syncing with a contest"),
                    ("manual", "Manual score input"),
                ],
                default="new",
                help_text="Choose `manual score input` to avoid synchronization with contest results",
                max_length=15,
                verbose_name="Status",
            ),
        ),
    ]
