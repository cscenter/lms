# Generated by Django 2.2.10 on 2020-03-30 18:36
import core.timezone.fields
import core.timezone.models
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("admission", "0005_auto_20200304_1300"),
    ]

    operations = [
        migrations.AlterField(
            model_name="campaign",
            name="application_ends_at",
            field=core.timezone.fields.TimezoneAwareDateTimeField(
                help_text="Last day for submitting application",
                verbose_name="Application Ends on",
            ),
        ),
        migrations.AlterField(
            model_name="campaign",
            name="application_starts_at",
            field=core.timezone.fields.TimezoneAwareDateTimeField(
                verbose_name="Application Starts on"
            ),
        ),
        migrations.AlterField(
            model_name="interview",
            name="date",
            field=core.timezone.fields.TimezoneAwareDateTimeField(verbose_name="When"),
        ),
    ]
