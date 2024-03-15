# Generated by Django 3.2.18 on 2024-03-15 09:14

import admission.models
from django.db import migrations
import sorl.thumbnail.fields


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0050_auto_20240315_0853'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applicant',
            name='photo',
            field=sorl.thumbnail.fields.ImageField(blank=True, help_text='Applicant|photo', upload_to=admission.models.applicant_photo_upload_to, verbose_name='Applicant photo'),
        ),
    ]
