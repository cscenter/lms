# -*- coding: utf-8 -*-
# Generated by Django 1.9.12 on 2017-04-12 09:23
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='applicant',
            old_name='last_name',
            new_name='patronymic',
        ),
        migrations.RenameField(
            model_name='applicant',
            old_name='second_name',
            new_name='surname',
        ),
    ]
