# Generated by Django 2.2.10 on 2020-05-28 11:37

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("admission", "0010_auto_20200527_1710"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="interviewformat",
            name="appointment_template",
        ),
    ]
