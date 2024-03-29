# Generated by Django 3.0.9 on 2020-09-02 08:19

from django.db import migrations
import files.models
import projects.models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0007_auto_20200902_0811'),
    ]

    operations = [
        migrations.AlterField(
            model_name='report',
            name='file',
            field=files.models.ConfigurableStorageFileField(blank=True, max_length=200, null=True, upload_to=projects.models.report_file_upload_to, verbose_name='Report file'),
        ),
        migrations.AlterField(
            model_name='reportcomment',
            name='attached_file',
            field=files.models.ConfigurableStorageFileField(blank=True, max_length=200, upload_to=projects.models.report_comment_attachment_upload_to),
        ),
    ]
