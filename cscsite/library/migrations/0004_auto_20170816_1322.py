# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-08-16 13:22
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0003_auto_20170816_1248'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='book',
            name='copies',
        ),
        migrations.RemoveField(
            model_name='book',
            name='read_by',
        ),
        migrations.RemoveField(
            model_name='borrow',
            name='book',
        ),
        migrations.RemoveField(
            model_name='stock',
            name='read_by',
        ),
    ]
