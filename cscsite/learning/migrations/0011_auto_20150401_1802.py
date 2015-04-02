# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from learning.models import StudentProjectTimeframe


def forwards_func(apps, schema_editor):
    SPT = apps.get_model('learning', 'StudentProjectTimeframe')
    SP = apps.get_model('learning', 'StudentProject')
    db_alias = schema_editor.connection.alias
    type_map = {'autumn': StudentProjectTimeframe.AUTUMN,
                'spring': StudentProjectTimeframe.SPRING}
    for sp in SP.objects.using(db_alias).all():
        tfs = [(SPT.objects.using(db_alias)
                .get_or_create(year=sem.year,
                               type=type_map[sem.type]))
               for sem in sp.semesters.all()]
        for tf, created in tfs:
            if created:
                tf.save()
            sp.timeframes.add(tf)

def backwards_func(apps, schema_editor):
    SP = apps.get_model('learning', 'StudentProject')
    Sem = apps.get_model('learning', 'Semester')
    db_alias = schema_editor.connection.alias
    type_map = {StudentProjectTimeframe.AUTUMN: 'autumn',
                StudentProjectTimeframe.SPRING: 'spring'}
    for sp in SP.objects.using(db_alias).all():
        sems = [(Sem.objects.using(db_alias)
                 .get_or_create(year=tfs.year,
                                type=type_map[tfs.type]))
                for tfs in sp.timeframes.all()]
        for sem, created in sems:
            if created:
                sem.save()
            sp.semesters.add(sem)


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0010_auto_20150401_1747'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='studentprojecttimeframe',
            unique_together=set([('year', 'type')]),
        ),
        migrations.RunPython(forwards_func, backwards_func),
    ]
