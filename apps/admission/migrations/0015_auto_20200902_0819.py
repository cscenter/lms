# Generated by Django 3.0.9 on 2020-09-02 08:19

import admission.models
from django.db import migrations
import files.models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0014_auto_20200818_2211'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contest',
            name='file',
            field=files.models.ConfigurableStorageFileField(blank=True, max_length=200, upload_to=admission.models.contest_assignments_upload_to, verbose_name='Assignments in pdf format'),
        ),
    ]
