# Generated by Django 2.2.4 on 2019-08-14 09:42

from django.db import migrations


def copy_branch(apps, schema_editor):
    M = apps.get_model('users', 'user')
    for o in M.objects.select_related('branch'):
        if o.branch_id:
            o.branch_new2_id = o.branch.id
            o.save(update_fields=["branch_new2_id"])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0018_user_branch_new2'),
    ]

    operations = [
        migrations.RunPython(copy_branch)
    ]
