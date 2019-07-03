# Generated by Django 2.2.3 on 2019-07-03 11:25

from django.db import migrations

from users.constants import AcademicRoles


def create_groups(apps, schema_editor):
    Group = apps.get_model('users', 'Group')
    for group_id, group_name in AcademicRoles.values.items():
        Group.objects.update_or_create(
            pk=group_id,
            defaults={
                "name": group_name
            }
        )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_auto_20190703_1123'),
    ]

    operations = [
        migrations.RunPython(create_groups),
    ]
