# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-07-14 14:24
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0017_auto_20160714_1636'),
        ('projects', '0001_initial'),  # Make sure the projects db state is setup
    ]

    # This needs to be a state-only operation because the database model was
    # renamed, and no longer exists according to Django.
    state_operations = [
        # Pasted from auto-generated operations in previous step:
        migrations.DeleteModel(
            name='StudentProject',
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=state_operations)
    ]
