# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):
    def forward(apps, schema_editor):
        Assignment = apps.get_model("learning", "Assignment")
        AssignmentAttachment = apps.get_model("learning",
                                              "AssignmentAttachment")
        for a in Assignment.objects.all():
            if a.attached_file:
                (AssignmentAttachment.objects
                 .create(assignment=a,
                         attachment=a.attached_file))

    def backward(apps, schema_editor):
        Assignment = apps.get_model("learning", "Assignment")
        AssignmentAttachment = apps.get_model("learning",
                                              "AssignmentAttachment")
        for aa in AssignmentAttachment.objects.all():
            if aa.attachment:
                aa.assignment.attached_file = aa.attachment
                aa.assignment.save()


    dependencies = [
        ('learning', '0004_data_add_studyprograms'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssignmentAttachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('attachment', models.FileField(upload_to='assignment_attachments')),
                ('assignment', models.ForeignKey(verbose_name='Assignment', to='learning.Assignment')),
            ],
            options={
                'ordering': ['assignment', '-created'],
                'verbose_name': 'Assignment attachment',
                'verbose_name_plural': 'Assignment attachments',
            },
            bases=(models.Model, object),
        ),
        migrations.RunPython(forward, backward),
    ]
