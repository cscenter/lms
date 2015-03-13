# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def remove_studyprograms(apps, schema_editor):
    StudyProgram = apps.get_model('learning', 'StudyProgram')
    db_alias = schema_editor.connection.alias
    StudyProgram.objects.using(db_alias).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('learning', '0006_remove_assignment_attached_file'),
    ]

    operations = [
        migrations.CreateModel(
            name='City',
            fields=[
                ('code', models.CharField(max_length=5, serialize=False, verbose_name='PK|Code', primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='City|Name')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'City',
                'verbose_name_plural': 'Cities',
            },
            bases=(models.Model,),
        ),
        migrations.RemoveField(
            model_name='studyprogram',
            name='created',
        ),
        migrations.RemoveField(
            model_name='studyprogram',
            name='id',
        ),
        migrations.RemoveField(
            model_name='studyprogram',
            name='modified',
        ),
        migrations.RunPython(remove_studyprograms),
        migrations.AddField(
            model_name='studyprogram',
            name='code',
            field=models.CharField(default=42, max_length=2, serialize=False, verbose_name='PK|Code', primary_key=True),
            preserve_default=False,
        ),
    ]
