# Generated by Django 3.2.18 on 2024-07-29 06:29

from django.db import migrations


def make_many_branches(apps, schema_editor):
    """
        Adds the Branch object in Invitation.branch to the
        many-to-many relationship in Invitation.branches
    """
    Invitation = apps.get_model('learning', 'Invitation')

    for invitation in Invitation.objects.all():
        invitation.branches.add(invitation.branch)


class Migration(migrations.Migration):
    dependencies = [
        ('learning', '0046_auto_20240729_0626'),
    ]

    operations = [
        migrations.RunPython(make_many_branches)
    ]
