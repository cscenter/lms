# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def recalculate_semester_indexes(apps, schema_editor):
    from django.core.management import call_command
    call_command('recalculate_semester_indexes')


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0002_auto_20160122_1858'),
    ]

    operations = [
        migrations.AddField(
            model_name='semester',
            name='index',
            field=models.PositiveSmallIntegerField(default=0, help_text='System field. Do not manually edit', verbose_name='Semester index', editable=False),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='semester',
            unique_together=set([('year', 'type')]),
        ),
        migrations.RunPython(recalculate_semester_indexes),
    ]
