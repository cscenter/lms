# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def forward_func(apps, schema_editor):
    Textpage = apps.get_model('textpages', 'Textpage')
    db_alias = schema_editor.connection.alias
    Textpage.objects.using(db_alias).bulk_create([
        Textpage(url_name='enrollment_application',
                 name="Enrollment application",
                 text="# Enrollment application\n\n**PLEASE CHANGE ME**"),
    ])

def backward_func(apps, schema_editor):
    Textpage = apps.get_model('textpages', 'Textpage')
    db_alias = schema_editor.connection.alias
    (Textpage.objects.using(db_alias)
     .filter(url_name='enrollment_application')
     .delete())


class Migration(migrations.Migration):

    dependencies = [
        ('textpages', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(forward_func, backward_func),
    ]
