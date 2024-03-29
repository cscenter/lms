# Generated by Django 2.2.4 on 2019-08-30 08:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("admission", "0001_initial"),
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="university",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="core.Branch",
                verbose_name="Branch",
            ),
        ),
        migrations.AddField(
            model_name="test",
            name="applicant",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="online_test",
                to="admission.Applicant",
                verbose_name="Applicant",
            ),
        ),
        migrations.AddField(
            model_name="interviewstream",
            name="campaign",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="interview_streams",
                to="admission.Campaign",
                verbose_name="Campaign",
            ),
        ),
    ]
