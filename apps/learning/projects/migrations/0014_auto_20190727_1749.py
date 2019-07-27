# Generated by Django 2.2.3 on 2019-07-27 17:49

from django.db import migrations


def copy_branch(apps, schema_editor):
    ReportingPeriod = apps.get_model('projects', 'ReportingPeriod')
    for sp in ReportingPeriod.objects.select_related('branch'):
        if sp.branch_id:
            sp.branch_new_id = sp.branch.code
            sp.save(update_fields=['branch_new_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0013_auto_20190727_1748'),
    ]

    operations = [
        migrations.RunPython(copy_branch)
    ]
