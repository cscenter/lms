# Generated by Django 3.0.9 on 2021-02-18 10:33

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("admission", "0018_auto_20210217_1523"),
    ]

    operations = [
        migrations.RenameField(
            model_name="applicant",
            old_name="surname",
            new_name="last_name",
        ),
        migrations.AlterField(
            model_name="applicant",
            name="yandex_login_q",
            field=models.CharField(
                blank=True,
                editable=False,
                help_text="Applicant|yandex_id_normalization",
                max_length=80,
                null=True,
                verbose_name="Yandex Login (normalized)",
            ),
        ),
    ]
