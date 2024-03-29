# Generated by Django 3.1.12 on 2021-07-22 14:15

import core.timezone.fields
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):
    dependencies = [
        ("admission", "0038_interview_venue"),
    ]

    operations = [
        migrations.AddField(
            model_name="campaign",
            name="confirmation_ends_at",
            field=core.timezone.fields.TimezoneAwareDateTimeField(
                blank=True,
                help_text="Deadline for accepting invitation to create student profile",
                null=True,
                verbose_name="Confirmation Ends on",
            ),
        ),
        migrations.CreateModel(
            name="Acceptance",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="created",
                    ),
                ),
                (
                    "modified_at",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="modified",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("new", "Waiting for Confirmation"),
                            ("confirmed", "Confirmed"),
                        ],
                        default="new",
                        max_length=12,
                        verbose_name="Status",
                    ),
                ),
                (
                    "access_key",
                    models.CharField(db_index=True, editable=False, max_length=128),
                ),
                (
                    "confirmation_code",
                    models.CharField(
                        editable=False, max_length=24, verbose_name="Confirmation Code"
                    ),
                ),
                (
                    "applicant",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="admission.applicant",
                        verbose_name="Applicant",
                    ),
                ),
            ],
            options={
                "verbose_name": "Acceptance for Studies",
                "verbose_name_plural": "Acceptances for Studies",
            },
        ),
    ]
