# Generated by Django 2.2.10 on 2020-05-27 17:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("admission", "0009_auto_20200527_1709"),
    ]

    operations = [
        migrations.AddField(
            model_name="interviewstream",
            name="format",
            field=models.CharField(
                choices=[("offline", "Offline"), ("online", "Online")],
                default="offline",
                max_length=42,
                verbose_name="Interview Format",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="interviewstream",
            name="interview_format",
            field=models.ForeignKey(
                default=1,
                editable=False,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="admission.InterviewFormat",
                verbose_name="Interview Format",
            ),
            preserve_default=False,
        ),
    ]
